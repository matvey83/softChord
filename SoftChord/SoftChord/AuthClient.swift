//
//  AuthClient.swift
//  SoftChord
//

import Foundation

nonisolated enum AuthError: Error, Equatable {
    case notConfigured
    case needsHTTPS
    case redirectRefused
    case invalidEmail
    case missingVerifier
    case missingToken
    case storage
    case transport
    case rejected(status: Int, code: String?)
}

nonisolated struct AuthHTTPResponse: Sendable, Equatable {
    var status: Int
    var body: Data
}

/// A stand-in for `URLSession` so tests can answer without the network.
nonisolated protocol AuthHTTPSending: Sendable {
    func send(_ request: URLRequest) async throws -> AuthHTTPResponse
}

/// Refuses redirects. An authenticated redirect would send the bearer token to the new host.
nonisolated final class RedirectRefusal: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        willPerformHTTPRedirection response: HTTPURLResponse,
        newRequest request: URLRequest
    ) async -> URLRequest? {
        if Self.carriesBearer(task.originalRequest) || Self.carriesBearer(request) {
            return nil
        }
        return nil
    }

    static func carriesBearer(_ request: URLRequest?) -> Bool {
        request?.value(forHTTPHeaderField: "Authorization") != nil
    }
}

nonisolated final class URLSessionAuthTransport: AuthHTTPSending, @unchecked Sendable {
    private let session: URLSession
    private let redirects: RedirectRefusal

    init() {
        let redirects = RedirectRefusal()
        let configuration = URLSessionConfiguration.ephemeral
        configuration.httpShouldSetCookies = false
        configuration.httpCookieAcceptPolicy = .never
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.urlCache = nil
        configuration.timeoutIntervalForRequest = AuthTiming.requestTimeout
        configuration.waitsForConnectivity = false
        self.redirects = redirects
        self.session = URLSession(configuration: configuration, delegate: redirects, delegateQueue: nil)
    }

    func send(_ request: URLRequest) async throws -> AuthHTTPResponse {
        let session = self.session
        return try await Task.detached {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                throw AuthError.transport
            }
            return AuthHTTPResponse(status: http.statusCode, body: data)
        }.value
    }
}

/// Passwordless sign-in against the magic-link contract.
nonisolated final class AuthClient: @unchecked Sendable {
    let origin: APIOrigin
    private let transport: any AuthHTTPSending
    private let store: any SessionStoring
    private let randomBytes: @Sendable () throws -> Data
    private let now: @Sendable () -> Date

    init(
        originRaw: String?,
        transport: any AuthHTTPSending,
        store: any SessionStoring,
        randomBytes: @escaping @Sendable () throws -> Data = { try AuthVerifier.randomBytes() },
        now: @escaping @Sendable () -> Date = { Date() }
    ) {
        self.origin = APIOrigin.resolve(originRaw)
        self.transport = transport
        self.store = store
        self.randomBytes = randomBytes
        self.now = now
    }

    var hasSession: Bool {
        guard let token = try? store.loadSession() else {
            return false
        }
        return AuthVerifier.isSessionToken(token)
    }

    var hasVerifier: Bool {
        expireVerifierIfNeeded()
        guard let verifier = try? store.loadVerifier() else {
            return false
        }
        return AuthVerifier.isVerifier(verifier)
    }

    /// Seconds left before the pending verifier is cleared. Zero when there is none.
    func pendingVerifierRemaining() -> TimeInterval {
        expireVerifierIfNeeded()
        guard let issued = try? store.loadVerifierIssuedAt() else {
            return 0
        }
        return AuthTiming.verifierLifetime - now().timeIntervalSince(issued)
    }

    /// The pending verifier lasts 15 minutes. At 900 seconds it is cleared.
    func expireVerifierIfNeeded() {
        guard let issued = try? store.loadVerifierIssuedAt() else {
            if (try? store.loadVerifier()) != nil {
                try? store.clearVerifier()
            }
            return
        }
        if now().timeIntervalSince(issued) >= AuthTiming.verifierLifetime {
            try? store.clearVerifier()
        }
    }

    func clearLocal() throws {
        try store.clear()
    }

    func requestLink(email: String) async throws {
        let address = email.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !address.isEmpty else {
            throw AuthError.invalidEmail
        }
        let originURL = try allowedOrigin()
        let verifier = try AuthVerifier.make(bytes: try randomBytes())
        let body = try jsonObject([
            "email": address,
            "client": "ios",
            "verifier_hash": verifier.hash,
        ])
        let response = try await post(originURL, path: "/api/auth/request-link", body: body, bearer: nil)
        try requireOK(response)
        try store.saveVerifier(verifier.value, issuedAt: now())
    }

    /// Returns the session token. The caller stores it only if this sign-in was not cancelled.
    func verify(token: String, deviceLabel: String) async throws -> String {
        let originURL = try allowedOrigin()
        expireVerifierIfNeeded()
        guard let verifier = try store.loadVerifier(), AuthVerifier.isVerifier(verifier) else {
            throw AuthError.missingVerifier
        }
        let label = deviceLabelText(deviceLabel)
        let body = try jsonObject([
            "token": token,
            "verifier": verifier,
            "device_label": label,
        ])
        let response = try await post(originURL, path: "/api/auth/verify", body: body, bearer: nil)
        guard response.status == 200 else {
            throw AuthError.rejected(status: response.status, code: errorCode(response.body))
        }
        guard let object = jsonDictionary(response.body),
              let session = object["token"] as? String,
              AuthVerifier.isSessionToken(session)
        else {
            throw AuthError.missingToken
        }
        return session
    }

    /// Stores a session token only after it matches base64url, 43 to 128 characters.
    func storeSession(_ token: String) throws {
        guard AuthVerifier.isSessionToken(token) else {
            throw AuthError.missingToken
        }
        try store.saveSession(token)
        try? store.clearVerifier()
    }

    func currentEmail() async throws -> String {
        let originURL = try allowedOrigin()
        guard let session = try store.loadSession(), AuthVerifier.isSessionToken(session) else {
            throw AuthError.rejected(status: 401, code: "unauthorized")
        }
        let response = try await get(originURL, path: "/api/me", bearer: session)
        guard response.status == 200,
              let object = jsonDictionary(response.body),
              let email = object["email"] as? String,
              !email.isEmpty
        else {
            throw AuthError.rejected(status: response.status, code: errorCode(response.body))
        }
        return email
    }

    func logout() async throws {
        try await endSession(path: "/api/auth/logout")
    }

    func logoutEverywhere() async throws {
        try await endSession(path: "/api/auth/logout-all")
    }

    private func endSession(path: String) async throws {
        let originURL: URL
        switch origin {
        case .notConfigured, .needsHTTPS:
            try store.clear()
            return
        case .allowed(let url):
            originURL = url
        }
        guard let session = try store.loadSession(), AuthVerifier.isSessionToken(session) else {
            try store.clear()
            return
        }
        let response = try await post(originURL, path: path, body: Data("{}".utf8), bearer: session)
        if response.status == 200 || response.status == 401 {
            // A newer sign-in may have replaced the token while this call was in flight.
            if try store.loadSession() == session {
                try store.clear()
            }
            return
        }
        throw AuthError.rejected(status: response.status, code: errorCode(response.body))
    }

    private func allowedOrigin() throws -> URL {
        switch origin {
        case .notConfigured:
            throw AuthError.notConfigured
        case .needsHTTPS:
            throw AuthError.needsHTTPS
        case .allowed(let url):
            return url
        }
    }

    private func post(_ origin: URL, path: String, body: Data, bearer: String?) async throws -> AuthHTTPResponse {
        var request = URLRequest(url: try endpoint(origin, path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = body
        return try await send(request, bearer: bearer)
    }

    private func get(_ origin: URL, path: String, bearer: String) async throws -> AuthHTTPResponse {
        var request = URLRequest(url: try endpoint(origin, path))
        request.httpMethod = "GET"
        return try await send(request, bearer: bearer)
    }

    private func send(_ request: URLRequest, bearer: String?) async throws -> AuthHTTPResponse {
        var request = request
        request.httpShouldHandleCookies = false
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = AuthTiming.requestTimeout
        if let bearer {
            // The bearer token is sent and never logged.
            request.setValue("Bearer \(bearer)", forHTTPHeaderField: "Authorization")
        }
        let outbound = request
        let transport = self.transport
        let response = try await Task.detached(priority: .userInitiated) {
            try await transport.send(outbound)
        }.value
        if (300..<400).contains(response.status) {
            throw AuthError.redirectRefused
        }
        return response
    }

    private func endpoint(_ origin: URL, _ path: String) throws -> URL {
        guard var parts = URLComponents(url: origin, resolvingAgainstBaseURL: false) else {
            throw AuthError.transport
        }
        parts.path = path
        parts.query = nil
        parts.fragment = nil
        guard let url = parts.url else {
            throw AuthError.transport
        }
        return url
    }

    private func requireOK(_ response: AuthHTTPResponse) throws {
        guard response.status == 200,
              let object = jsonDictionary(response.body),
              object["ok"] as? Bool == true
        else {
            throw AuthError.rejected(status: response.status, code: errorCode(response.body))
        }
    }

    private func jsonObject(_ fields: [String: String]) throws -> Data {
        let data = try JSONSerialization.data(withJSONObject: fields, options: [.sortedKeys])
        guard jsonDictionary(data) != nil else {
            throw AuthError.storage
        }
        return data
    }

    private func jsonDictionary(_ data: Data) -> [String: Any]? {
        (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
    }

    private func errorCode(_ data: Data) -> String? {
        jsonDictionary(data)?["error"] as? String
    }

    private func deviceLabelText(_ label: String) -> String {
        let trimmed = label.trimmingCharacters(in: .whitespacesAndNewlines)
        let value = trimmed.isEmpty ? "iOS" : trimmed
        return String(value.prefix(200))
    }
}

nonisolated enum AuthTiming {
    static let verifierLifetime: TimeInterval = 900
    static let requestTimeout: TimeInterval = 15
}
