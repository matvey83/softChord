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
    static let signOut = "Sign out"
    static let signOutEverywhere = "Sign Out Everywhere"
    static let verifyFailed = "Open this link on the device where you requested it."
    static let unreachable = "Could not reach SoftChord."
    static let invalidEmail = "Enter an email address."
    static let badEmail = "That email address is not valid."
    static let couldNotSignOut = "Could not sign out."
    static let couldNotLoad = "Could not load the account."
    static let signedIn = "Signed in"
    static let retry = "Retry"
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

    let client: AuthClient
    private let deviceLabel: String
    private var didRestore = false

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
        guard applyOriginGate() else {
            return
        }
        if client.hasSession {
            await loadEmail()
            return
        }
        if client.hasVerifier {
            phase = .checkEmail
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
        busy = true
        defer { busy = false }
        do {
            try await client.requestLink(email: email)
            phase = .checkEmail
            banner = nil
        } catch {
            banner = message(for: error, signingOut: false)
        }
    }

    func open(url: URL) async {
        guard applyOriginGate() else {
            return
        }
        switch LoginLink.classify(url) {
        case .ignore:
            return
        case .invalid:
            banner = AuthCopy.verifyFailed
        case .token(let token):
            await verify(token: token)
        }
    }

    func open(pasted text: String) async {
        guard applyOriginGate() else {
            return
        }
        switch LoginLink.classify(pasted: text) {
        case .ignore, .invalid:
            banner = AuthCopy.verifyFailed
        case .token(let token):
            await verify(token: token)
        }
    }

    func reloadAccount() async {
        guard !busy else {
            return
        }
        guard applyOriginGate() else {
            return
        }
        busy = true
        defer { busy = false }
        await loadEmail()
    }

    func editEmailAgain() {
        guard !busy, case .allowed = client.origin else {
            return
        }
        phase = .signedOut
        banner = nil
        pastedLink = ""
    }

    func signOut() async {
        await endSession(everywhere: false)
    }

    func signOutEverywhere() async {
        await endSession(everywhere: true)
    }

    private func verify(token: String) async {
        guard !busy else {
            return
        }
        busy = true
        defer { busy = false }
        do {
            try await client.verify(token: token, deviceLabel: deviceLabel)
        } catch {
            banner = message(for: error, signingOut: false)
            return
        }
        await loadEmail()
    }

    private func loadEmail() async {
        do {
            let email = try await client.currentEmail()
            phase = .signedIn(email: email)
            banner = nil
            pastedLink = ""
        } catch {
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
        guard !busy else {
            return
        }
        busy = true
        defer { busy = false }
        do {
            if everywhere {
                try await client.logoutEverywhere()
            } else {
                try await client.logout()
            }
            emailDraft = ""
            pastedLink = ""
            banner = nil
            phase = signedOutPhase()
        } catch {
            banner = message(for: error, signingOut: true)
        }
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

    private func message(for error: Error, signingOut: Bool) -> String {
        guard let error = error as? AuthError else {
            return signingOut ? AuthCopy.couldNotSignOut : AuthCopy.unreachable
        }
        switch error {
        case .notConfigured:
            return AuthCopy.notConfigured
        case .needsHTTPS:
            return AuthCopy.needsHTTPS
        case .invalidEmail:
            return AuthCopy.invalidEmail
        case .redirectRefused, .storage, .transport:
            return signingOut ? AuthCopy.couldNotSignOut : AuthCopy.unreachable
        case .missingVerifier, .missingToken:
            return AuthCopy.verifyFailed
        case .rejected(_, let code):
            if signingOut {
                return AuthCopy.couldNotSignOut
            }
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
