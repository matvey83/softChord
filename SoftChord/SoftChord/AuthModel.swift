//
//  AuthModel.swift
//  SoftChord
//

import Combine
import Foundation
import UIKit

nonisolated enum AuthCopy {
    static let notConfigured = "Sign-in not configured"
    static let needsHTTPS = "Sign-in requires HTTPS."
    static let checkEmail = "Check your email"
    static let emailLink = "Email me a link"
    static let continueLink = "Continue"
    static let differentEmail = "Use a different email"
    static let cancel = "Cancel"
    static let signOut = "Sign out"
    static let signOutEverywhere = "Sign Out Everywhere"
    static let signOutEverywherePrompt = "Sign out of every device?"
    static let verifyFailed = "Open this link on the device where you requested it."
    static let unreachable = "Could not reach SoftChord."
    static let invalidEmail = "Enter an email address."
    static let badEmail = "That email address is not valid."
    static let couldNotSignOut = "Could not sign out."
    static let couldNotSignOutEverywhere = "Could not sign out everywhere."
    static let couldNotLoad = "Could not load the account."
    static let signedIn = "Signed in"
    static let retry = "Retry"
    static let linkWaiting = "This link will be used when the current sign-in finishes."
}

@MainActor
final class AuthModel: ObservableObject {
    enum Phase: Equatable {
        case notConfigured
        case needsHTTPS
        case signedOut
        case checkEmail
        case signedIn(email: String?)
    }

    @Published private(set) var phase: Phase
    @Published var emailDraft: String
    @Published var pastedLink: String
    @Published private(set) var banner: String?
    @Published private(set) var busy: Bool
    @Published var confirmSignOutEverywhere = false

    let client: AuthClient
    private let deviceLabel: String
    private var didRestore = false
    /// Bumped when sign-in is dismissed or a session is replaced, so a late response is ignored.
    private var generation = 0
    /// In-flight calls. Sign-out must not clear `busy` while another call is still running.
    private var operations = 0
    private var queuedToken: String?

    static let shared = AuthModel()

    convenience init() {
        self.init(
            client: AuthClient(
                originRaw: APIOrigin.plistValue(),
                transport: URLSessionAuthTransport(),
                store: KeychainSessionStore()
            ),
            deviceLabel: UIDevice.current.model
        )
    }

    init(client: AuthClient, deviceLabel: String) {
        self.client = client
        let trimmed = deviceLabel.trimmingCharacters(in: .whitespacesAndNewlines)
        self.deviceLabel = String((trimmed.isEmpty ? "iOS" : trimmed).prefix(200))
        emailDraft = ""
        pastedLink = ""
        banner = nil
        busy = false
        switch client.origin {
        case .notConfigured:
            phase = .notConfigured
        case .needsHTTPS:
            phase = .needsHTTPS
        case .allowed:
            phase = .signedOut
        }
    }

    var statusText: String? {
        switch phase {
        case .notConfigured:
            return AuthCopy.notConfigured
        case .needsHTTPS:
            return AuthCopy.needsHTTPS
        case .checkEmail:
            return AuthCopy.checkEmail
        case .signedOut, .signedIn:
            return nil
        }
    }

    func restore() async {
        guard !didRestore else {
            return
        }
        didRestore = true
        refreshPendingLink()
        guard applyOriginGate() else {
            return
        }
        if client.hasSession {
            await loadEmail(ticket: generation)
            return
        }
        if client.hasVerifier {
            phase = .checkEmail
        }
    }

    /// Seconds until "Check your email" should be cleared. Zero when it is already due.
    func pendingLinkRemaining() -> TimeInterval {
        client.pendingVerifierRemaining()
    }

    /// Drops "Check your email" once the verifier is 900 seconds old.
    func refreshPendingLink() {
        client.expireVerifierIfNeeded()
        guard case .checkEmail = phase else {
            return
        }
        if !client.hasVerifier {
            phase = signedOutPhase()
            banner = nil
        }
    }

    func requestLink() async {
        guard !busy else {
            return
        }
        guard applyOriginGate() else {
            return
        }
        let email = emailDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !email.isEmpty else {
            banner = AuthCopy.invalidEmail
            return
        }
        let ticket = generation
        beginOperation()
        defer { endOperation() }
        do {
            try await client.requestLink(email: email)
            guard ticket == generation else {
                return
            }
            phase = .checkEmail
            banner = nil
        } catch {
            guard ticket == generation else {
                return
            }
            banner = message(for: error, everywhere: false)
        }
        await drainQueue()
    }

    func open(url: URL) async {
        await receive(LoginLink.classify(url, origin: client.origin))
    }

    func open(pasted text: String) async {
        await receive(LoginLink.classify(pasted: text, origin: client.origin))
    }

    func reloadAccount() async {
        guard applyOriginGate() else {
            return
        }
        let ticket = generation
        beginOperation()
        defer { endOperation() }
        await loadEmail(ticket: ticket)
    }

    func dismissSignIn() {
        generation += 1
        queuedToken = nil
        banner = nil
        pastedLink = ""
        if case .signedIn = phase {
            return
        }
        phase = signedOutPhase()
    }

    func editEmailAgain() {
        dismissSignIn()
    }

    func requestSignOutEverywhere() {
        confirmSignOutEverywhere = true
    }

    func signOut() async {
        await endSession(everywhere: false)
    }

    func signOutEverywhere() async {
        confirmSignOutEverywhere = false
        await endSession(everywhere: true)
    }

    private func receive(_ result: LoginLinkResult) async {
        switch result {
        case .ignore:
            return
        case .invalid:
            banner = AuthCopy.verifyFailed
        case .token(let token):
            guard applyOriginGate() else {
                return
            }
            if busy {
                queuedToken = token
                banner = AuthCopy.linkWaiting
                return
            }
            await verify(token: token)
            await drainQueue()
        }
    }

    private func verify(token: String) async {
        generation += 1
        let ticket = generation
        beginOperation()
        defer { endOperation() }
        do {
            let session = try await client.verify(token: token, deviceLabel: deviceLabel)
            guard ticket == generation else {
                return
            }
            try storeSession(session)
            await loadEmail(ticket: generation)
        } catch {
            guard ticket == generation else {
                return
            }
            banner = message(for: error, everywhere: false)
        }
    }

    /// Saving a session retires every call that still belongs to the previous token.
    private func storeSession(_ token: String) throws {
        try client.storeSession(token)
        generation += 1
    }

    private func loadEmail(ticket: Int) async {
        do {
            let email = try await client.currentEmail()
            guard ticket == generation else {
                return
            }
            phase = .signedIn(email: email)
            banner = nil
            pastedLink = ""
        } catch {
            guard ticket == generation else {
                return
            }
            if case AuthError.rejected(let status, _) = error, status == 401 {
                try? client.clearLocal()
                phase = signedOutPhase()
                banner = nil
                return
            }
            if client.hasSession {
                phase = .signedIn(email: nil)
            }
            banner = AuthCopy.couldNotLoad
        }
    }

    private func endSession(everywhere: Bool) async {
        generation += 1
        let ticket = generation
        queuedToken = nil
        beginOperation()
        defer { endOperation() }
        do {
            if everywhere {
                try await client.logoutEverywhere()
            } else {
                try await client.logout()
            }
            guard ticket == generation else {
                return
            }
            emailDraft = ""
            pastedLink = ""
            banner = nil
            phase = signedOutPhase()
        } catch {
            guard ticket == generation else {
                return
            }
            banner = message(for: error, everywhere: everywhere, signingOut: true)
        }
    }

    private func drainQueue() async {
        guard let token = queuedToken else {
            return
        }
        queuedToken = nil
        if case .signedIn = phase {
            return
        }
        await verify(token: token)
    }

    @discardableResult
    private func applyOriginGate() -> Bool {
        switch client.origin {
        case .notConfigured:
            phase = .notConfigured
            return false
        case .needsHTTPS:
            phase = .needsHTTPS
            return false
        case .allowed:
            return true
        }
    }

    private func beginOperation() {
        operations += 1
        busy = true
    }

    private func endOperation() {
        operations = max(0, operations - 1)
        busy = operations > 0
    }

    private func signedOutPhase() -> Phase {
        switch client.origin {
        case .notConfigured:
            return .notConfigured
        case .needsHTTPS:
            return .needsHTTPS
        case .allowed:
            return .signedOut
        }
    }

    private func message(for error: Error, everywhere: Bool, signingOut: Bool = false) -> String {
        if everywhere {
            return AuthCopy.couldNotSignOutEverywhere
        }
        if signingOut {
            return AuthCopy.couldNotSignOut
        }
        guard let error = error as? AuthError else {
            return AuthCopy.unreachable
        }
        switch error {
        case .notConfigured:
            return AuthCopy.notConfigured
        case .needsHTTPS:
            return AuthCopy.needsHTTPS
        case .invalidEmail:
            return AuthCopy.invalidEmail
        case .redirectRefused, .storage, .transport:
            return AuthCopy.unreachable
        case .missingVerifier, .missingToken:
            return AuthCopy.verifyFailed
        case .rejected(_, let code):
            if code == "invalid_request" {
                return AuthCopy.badEmail
            }
            if code == "invalid_or_expired" {
                return AuthCopy.verifyFailed
            }
            return AuthCopy.unreachable
        }
    }
}
