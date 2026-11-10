//
//  AuthTests.swift
//  SoftChordTests
//

import Foundation
import XCTest
@testable import SoftChord

/// SHA-256 of SoftChordTests/api-contract.json.
/// Copied byte-for-byte from server commit 0775e8211158c57ff0869d1dbcf961c72ef167bd.
private let contractSHA256 = "9f213067d7a0e262a998175848dd58c1021443dd04f3abc56881b19df1c990d5"

/// Raw 32 bytes of the contract verifier `Gom_dJiEsQeMik8sm58Q4xt4rDESd-H8z2s-jNvPnAE`.
private let contractVerifierBytes = Data([
    0x1a, 0x89, 0xbf, 0x74, 0x98, 0x84, 0xb1, 0x07,
    0x8c, 0x8a, 0x4f, 0x2c, 0x9b, 0x9f, 0x10, 0xe3,
    0x1b, 0x78, 0xac, 0x31, 0x12, 0x77, 0xe1, 0xfc,
    0xcf, 0x6b, 0x3e, 0x8c, 0xdb, 0xcf, 0x9c, 0x01,
])

/// A second contract token, used as a session token. It matches the bearer syntax.
private let sessionToken = "Qr4MgDAm0aB-s6pLkfOAoK-64CTFRrUNtVZLA0X-GJw"

/// Login token. Same base64url length as a session token.
private let loginToken = "Gom_dJiEsQeMik8sm58Q4xt4rDESd-H8z2s-jNvPnAE"

final class AuthTests: XCTestCase {
    func testContractFixtureMatchesTheServerBytes() throws {
        let data = try contractData()
        XCTAssertEqual(AuthVerifier.sha256Hex(data), contractSHA256)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let endpoints = try XCTUnwrap(json["endpoints"] as? [[String: Any]])
        let paths = endpoints.compactMap { $0["path"] as? String }
        XCTAssertTrue(paths.contains("/api/auth/logout-all"))
        XCTAssertTrue(paths.contains("/api/auth/request-link"))
    }

    func testVerifierMatchesTheContractVector() throws {
        let made = try AuthVerifier.make(bytes: contractVerifierBytes)
        let json = try contractJSON()
        let verifier = try XCTUnwrap(json["verifier"] as? [String: Any])
        XCTAssertEqual(made.value, "Gom_dJiEsQeMik8sm58Q4xt4rDESd-H8z2s-jNvPnAE")
        XCTAssertEqual(made.hash, "409a1dfd38791e76dbd352152207e00a8a3379fe17a96122eb07eb449b7d288e")
        XCTAssertEqual(made.value, verifier["value"] as? String)
        XCTAssertEqual(made.hash, verifier["sha256"] as? String)
        XCTAssertEqual(made.value.count, 43)
    }

    func testOriginRules() throws {
        XCTAssertEqual(APIOrigin.resolve(nil), .notConfigured)
        XCTAssertEqual(APIOrigin.resolve("   "), .notConfigured)
        XCTAssertEqual(APIOrigin.resolve("http://songs.example"), .needsHTTPS)
        XCTAssertEqual(APIOrigin.resolve("http://localhost.evil"), .needsHTTPS)
        XCTAssertEqual(APIOrigin.resolve("https://songs.example/api"), .notConfigured)
        XCTAssertEqual(APIOrigin.resolve("https://user@songs.example"), .notConfigured)
        XCTAssertEqual(APIOrigin.resolve("http://127.0.0.1.evil"), .needsHTTPS)
        XCTAssertEqual(APIOrigin.resolve("http://localhost@evil"), .notConfigured)
        XCTAssertEqual(APIOrigin.resolve("http://localhost@evil.com"), .notConfigured)

        guard case .allowed(let local) = APIOrigin.resolve("http://localhost:8787") else {
            return XCTFail("localhost should be allowed")
        }
        XCTAssertEqual(local.scheme, "http")
        XCTAssertEqual(local.host, "localhost")
        XCTAssertEqual(local.port, 8787)

        guard case .allowed(let loopback) = APIOrigin.resolve("http://127.0.0.1:8787") else {
            return XCTFail("127.0.0.1 should be allowed")
        }
        XCTAssertEqual(loopback.host, "127.0.0.1")

        guard case .allowed(let secure) = APIOrigin.resolve("https://songs.example") else {
            return XCTFail("https should be allowed")
        }
        XCTAssertEqual(secure.scheme, "https")
        XCTAssertEqual(secure.host, "songs.example")
    }

    func testRequestLinkShape() async throws {
        let parts = makeClient(bytes: contractVerifierBytes)
        try await parts.client.requestLink(email: "  singer@example.com  ")
        let request = try XCTUnwrap(parts.mock.requests.first)
        XCTAssertEqual(parts.mock.requests.count, 1)
        XCTAssertEqual(request.method, "POST")
        XCTAssertEqual(request.url.scheme, "https")
        XCTAssertEqual(request.url.host, "songs.example")
        XCTAssertEqual(request.url.path, "/api/auth/request-link")
        XCTAssertNil(request.url.query)
        XCTAssertEqual(request.headers, ["content-type": "application/json"])
        XCTAssertEqual(request.timeout, AuthTiming.requestTimeout)
        XCTAssertEqual(AuthTiming.requestTimeout, 15)
        let body = try jsonObject(request.body)
        XCTAssertEqual(body["client"] as? String, "ios")
        XCTAssertEqual(body["email"] as? String, "singer@example.com")
        XCTAssertEqual(body["verifier_hash"] as? String, "409a1dfd38791e76dbd352152207e00a8a3379fe17a96122eb07eb449b7d288e")
        XCTAssertEqual(Set(body.keys), ["client", "email", "verifier_hash"])
        XCTAssertEqual(try parts.store.loadVerifier(), "Gom_dJiEsQeMik8sm58Q4xt4rDESd-H8z2s-jNvPnAE")
        XCTAssertFalse(request.onMainThread)
    }

    func testEmptyEmailDoesNotCall() async throws {
        let parts = makeClient()
        do {
            try await parts.client.requestLink(email: "  ")
            XCTFail("empty email should not call")
        } catch AuthError.invalidEmail {
        }
        XCTAssertTrue(parts.mock.requests.isEmpty)
        XCTAssertNil(try parts.store.loadVerifier())
    }

    func testRejectedLinkDoesNotStoreTheVerifier() async throws {
        let parts = makeClient(bytes: contractVerifierBytes)
        parts.mock.handler = { _ in
            AuthHTTPResponse(status: 400, body: Data("{\"error\":\"invalid_request\"}".utf8))
        }
        do {
            try await parts.client.requestLink(email: "not-an-email")
            XCTFail("expected 400")
        } catch let error as AuthError {
            XCTAssertEqual(error, .rejected(status: 400, code: "invalid_request"))
        }
        XCTAssertNil(try parts.store.loadVerifier())
    }

    func testVerifyMeAndLogoutShapes() async throws {
        let parts = makeClient(bytes: contractVerifierBytes)
        parts.mock.handler = scripted
        try await parts.client.requestLink(email: "singer@example.com")
        let session = try await parts.client.verify(token: loginToken, deviceLabel: "  iPhone  ")
        try parts.client.storeSession(session)
        let email = try await parts.client.currentEmail()
        XCTAssertEqual(email, "singer@example.com")
        try await parts.client.logout()

        XCTAssertEqual(parts.mock.requests.map(\.url.path), [
            "/api/auth/request-link",
            "/api/auth/verify",
            "/api/me",
            "/api/auth/logout",
        ])
        let verify = parts.mock.requests[1]
        XCTAssertEqual(verify.method, "POST")
        XCTAssertEqual(verify.headers["content-type"], "application/json")
        XCTAssertNil(verify.headers["authorization"])
        let verifyBody = try jsonObject(verify.body)
        XCTAssertEqual(verifyBody["token"] as? String, loginToken)
        XCTAssertEqual(verifyBody["verifier"] as? String, "Gom_dJiEsQeMik8sm58Q4xt4rDESd-H8z2s-jNvPnAE")
        XCTAssertEqual(verifyBody["device_label"] as? String, "iPhone")
        XCTAssertEqual(Set(verifyBody.keys), ["device_label", "token", "verifier"])

        let me = parts.mock.requests[2]
        XCTAssertEqual(me.method, "GET")
        XCTAssertEqual(me.url.path, "/api/me")
        XCTAssertEqual(me.headers, ["authorization": "Bearer \(sessionToken)"])
        XCTAssertNil(me.body)

        let logout = parts.mock.requests[3]
        XCTAssertEqual(logout.method, "POST")
        XCTAssertEqual(logout.url.path, "/api/auth/logout")
        XCTAssertEqual(logout.headers, [
            "authorization": "Bearer \(sessionToken)",
            "content-type": "application/json",
        ])
        XCTAssertEqual(logout.body, Data("{}".utf8))
        XCTAssertNil(try parts.store.loadSession())
        XCTAssertNil(try parts.store.loadVerifier())
        XCTAssertTrue(parts.mock.requests.allSatisfy { !$0.onMainThread })
    }

    func testLogoutAllShape() async throws {
        let parts = makeClient()
        try parts.store.saveSession(sessionToken)
        try await parts.client.logoutEverywhere()
        let request = try XCTUnwrap(parts.mock.requests.first)
        XCTAssertEqual(parts.mock.requests.count, 1)
        XCTAssertEqual(request.method, "POST")
        XCTAssertEqual(request.url.path, "/api/auth/logout-all")
        XCTAssertEqual(request.headers, [
            "authorization": "Bearer \(sessionToken)",
            "content-type": "application/json",
        ])
        XCTAssertEqual(request.body, Data("{}".utf8))
        let object = try jsonObject(request.body)
        XCTAssertTrue(object.isEmpty)
        XCTAssertNil(try parts.store.loadSession())
    }

    func testMockRejectsAContentTypeThatIsNotExactlyJSON() async throws {
        let mock = MockAuthHTTP()
        let url = URL(string: "https://songs.example/api/auth/logout")!
        var plain = URLRequest(url: url)
        plain.httpMethod = "POST"
        plain.setValue("text/plain", forHTTPHeaderField: "Content-Type")
        plain.httpBody = Data("{}".utf8)
        let rejected = try await mock.send(plain)
        XCTAssertEqual(rejected.status, 400)

        var charset = URLRequest(url: url)
        charset.httpMethod = "POST"
        charset.setValue("application/json; charset=utf-8", forHTTPHeaderField: "Content-Type")
        charset.httpBody = Data("{}".utf8)
        let charsetResponse = try await mock.send(charset)
        XCTAssertEqual(charsetResponse.status, 400)

        var exact = URLRequest(url: url)
        exact.httpMethod = "POST"
        exact.setValue("application/json", forHTTPHeaderField: "Content-Type")
        exact.httpBody = Data("{}".utf8)
        let accepted = try await mock.send(exact)
        XCTAssertEqual(accepted.status, 200)
    }

    @MainActor
    func testRequestsLeaveTheMainThread() async throws {
        let parts = makeClient(bytes: contractVerifierBytes)
        try await parts.client.requestLink(email: "singer@example.com")
        let request = try XCTUnwrap(parts.mock.requests.first)
        XCTAssertFalse(request.onMainThread)
    }

    @MainActor
    func testUnsetOriginMakesNoRequest() async {
        let parts = makeClient(origin: "")
        let model = AuthModel(client: parts.client, deviceLabel: "iPhone")
        await model.restore()
        XCTAssertEqual(model.statusText, AuthCopy.notConfigured)
        XCTAssertEqual(model.statusText, "Sign-in not configured")
        model.emailDraft = "singer@example.com"
        await model.requestLink()
        await model.open(url: URL(string: "softchord://login?token=abc")!)
        await model.open(pasted: "https://songs.example/login#t=abc")
        await model.signOut()
        await model.signOutEverywhere()
        XCTAssertTrue(parts.mock.requests.isEmpty)
    }

    @MainActor
    func testHTTPOriginIsRejected() async throws {
        let parts = makeClient(origin: "http://songs.example")
        let model = AuthModel(client: parts.client, deviceLabel: "iPhone")
        XCTAssertEqual(model.statusText, "Sign-in requires HTTPS.")
        model.emailDraft = "singer@example.com"
        await model.requestLink()
        await model.open(pasted: "http://songs.example/login#t=abc")
        XCTAssertTrue(parts.mock.requests.isEmpty)

        do {
            try await parts.client.requestLink(email: "singer@example.com")
            XCTFail("http origin should not call")
        } catch AuthError.needsHTTPS {
        }
        XCTAssertTrue(parts.mock.requests.isEmpty)
    }

    func testLocalHTTPIsAllowed() async throws {
        let parts = makeClient(origin: "http://127.0.0.1:8787", bytes: contractVerifierBytes)
        try await parts.client.requestLink(email: "singer@example.com")
        let request = try XCTUnwrap(parts.mock.requests.first)
        XCTAssertEqual(request.url.scheme, "http")
        XCTAssertEqual(request.url.host, "127.0.0.1")
        XCTAssertEqual(request.url.port, 8787)
        XCTAssertEqual(request.url.path, "/api/auth/request-link")
        XCTAssertEqual(request.headers["content-type"], "application/json")
    }

    func testLoginLinkParsing() throws {
        let token = "Gom_dJiEsQeMik8sm58Q4xt4rDESd-H8z2s-jNvPnAE"
        let cases: [(String, LoginLinkResult)] = [
            ("softchord://login?token=\(token)", .token(token)),
            ("softchord://Login?token=\(token)", .token(token)),
            ("softchord://login/?token=\(token)", .token(token)),
            ("softchord://login?token=a%2Bb", .invalid),
            ("softchord://login?token=\(String(repeating: "a", count: 43))", .token(String(repeating: "a", count: 43))),
            ("softchord://login?token=\(String(repeating: "a", count: 42))", .invalid),
            ("softchord://login?token=\(String(repeating: "b", count: 128))", .token(String(repeating: "b", count: 128))),
            ("softchord://login?token=\(String(repeating: "b", count: 129))", .invalid),
            ("softchord://other?token=\(token)", .ignore),
            ("softchord://login", .invalid),
            ("softchord://login?token=", .invalid),
            ("softchord://login?token=\(String(repeating: "a", count: 201))", .invalid),
            ("https://songs.example/login?client=ios&hint=m%2A%2A%2A%40gmail.com#t=\(token)", .token(token)),
            ("https://songs.example/login#t=\(token)", .token(token)),
            ("https://songs.example/login#t=a%2Bb", .invalid),
            ("https://evil.example/login#t=\(token)", .invalid),
            ("https://songs.example/login?token=\(token)", .ignore),
            ("https://songs.example/songs#t=\(token)", .ignore),
            ("http://localhost:8787/login?client=ios#t=\(token)", .invalid),
            ("http://127.0.0.1/login#t=\(token)", .invalid),
            ("http://songs.example/login#t=\(token)", .invalid),
            ("https://user:pass@songs.example/login#t=\(token)", .invalid),
            ("https://songs.example/login#t=", .invalid),
        ]
        for (text, expected) in cases {
            let url = try XCTUnwrap(URL(string: text), text)
            XCTAssertEqual(LoginLink.classify(url, origin: songsOrigin), expected, text)
        }
        XCTAssertEqual(
            LoginLink.classify(pasted: " <softchord://login?token=\(token)> ", origin: songsOrigin),
            .token(token)
        )
        XCTAssertEqual(
            LoginLink.classify(pasted: "https://evil.example/login#t=\(token)", origin: songsOrigin),
            .invalid
        )
        XCTAssertEqual(LoginLink.classify(pasted: "not a link", origin: songsOrigin), .invalid)
        let local = APIOrigin.resolve("http://127.0.0.1:8787")
        let localURL = try XCTUnwrap(URL(string: "http://127.0.0.1:8787/login#t=\(token)"))
        XCTAssertEqual(LoginLink.classify(localURL, origin: local), .token(token))
        let localhost = APIOrigin.resolve("http://localhost:8787")
        let localhostURL = try XCTUnwrap(URL(string: "http://localhost:8787/login#t=\(token)"))
        XCTAssertEqual(LoginLink.classify(localhostURL, origin: localhost), .token(token))
    }

    func testRedirectIsRefusedAndDoesNotStoreASession() async throws {
        let parts = makeClient(bytes: contractVerifierBytes)
        try await parts.client.requestLink(email: "singer@example.com")
        parts.mock.removeAll()
        parts.mock.handler = { _ in
            AuthHTTPResponse(status: 302, body: Data("{\"email\":\"nope\"}".utf8))
        }
        do {
            _ = try await parts.client.verify(token: loginToken, deviceLabel: "iPhone")
            XCTFail("redirect should fail")
        } catch AuthError.redirectRefused {
        }
        XCTAssertEqual(parts.mock.requests.count, 1)
        XCTAssertFalse(parts.client.hasSession)
        XCTAssertEqual(try parts.store.loadVerifier(), "Gom_dJiEsQeMik8sm58Q4xt4rDESd-H8z2s-jNvPnAE")
    }

    func testRedirectDelegateReturnsNil() async throws {
        let delegate = RedirectRefusal()
        let session = URLSession(configuration: .ephemeral, delegate: delegate, delegateQueue: nil)
        defer { session.invalidateAndCancel() }
        let url = try XCTUnwrap(URL(string: "https://songs.example/api/me"))
        var authed = URLRequest(url: url)
        authed.setValue("Bearer \(sessionToken)", forHTTPHeaderField: "Authorization")
        let task = session.dataTask(with: authed)
        XCTAssertTrue(RedirectRefusal.carriesBearer(task.originalRequest))
        defer { task.cancel() }
        let response = try XCTUnwrap(HTTPURLResponse(
            url: url,
            statusCode: 302,
            httpVersion: nil,
            headerFields: ["Location": "https://evil.example/steal"]
        ))
        let next = URLRequest(url: try XCTUnwrap(URL(string: "https://evil.example/steal")))
        let followed = await delegate.urlSession(
            session,
            task: task,
            willPerformHTTPRedirection: response,
            newRequest: next
        )
        XCTAssertNil(followed)
    }

    func testFailedLogoutKeepsTheSession() async throws {
        let parts = makeClient()
        try parts.store.saveSession(sessionToken)
        parts.mock.handler = { _ in
            AuthHTTPResponse(status: 500, body: Data("{\"error\":\"nope\"}".utf8))
        }
        do {
            try await parts.client.logout()
            XCTFail("500 should fail")
        } catch let error as AuthError {
            XCTAssertEqual(error, .rejected(status: 500, code: "nope"))
        }
        XCTAssertEqual(try parts.store.loadSession(), sessionToken)

        parts.mock.transportError = URLError(.networkConnectionLost)
        do {
            try await parts.client.logoutEverywhere()
            XCTFail("transport failure should fail")
        } catch is URLError {
        }
        XCTAssertEqual(try parts.store.loadSession(), sessionToken)
        XCTAssertEqual(parts.mock.requests.count, 1)
    }

    func testAppInfoPlistDisablesSignInUntilAnOriginIsSet() {
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "SoftChordAPIOrigin") as? String, "")
    }

    func testAppInfoPlistRegistersTheLoginScheme() throws {
        let types = try XCTUnwrap(
            Bundle.main.object(forInfoDictionaryKey: "CFBundleURLTypes") as? [[String: Any]]
        )
        let schemes = types.flatMap { ($0["CFBundleURLSchemes"] as? [String]) ?? [] }
        XCTAssertTrue(schemes.contains("softchord"))
    }

    @MainActor
    func testSignInShowsTheEmailFromMeAndSignOutEverywhereClearsIt() async throws {
        let parts = makeClient(bytes: contractVerifierBytes)
        parts.mock.handler = scripted
        let model = AuthModel(client: parts.client, deviceLabel: "iPhone")
        model.emailDraft = "singer@example.com"
        await model.requestLink()
        XCTAssertEqual(model.phase, .checkEmail)
        XCTAssertEqual(model.statusText, "Check your email")
        await model.open(url: try XCTUnwrap(URL(string: "softchord://login?token=\(loginToken)")))
        XCTAssertEqual(model.phase, .signedIn(email: "singer@example.com"))
        XCTAssertEqual(parts.mock.requests.map(\.url.path), [
            "/api/auth/request-link",
            "/api/auth/verify",
            "/api/me",
        ])
        let verify = try jsonObject(parts.mock.requests[1].body)
        XCTAssertEqual(verify["device_label"] as? String, "iPhone")
        XCTAssertTrue(parts.mock.requests.allSatisfy { !$0.onMainThread })

        await model.signOutEverywhere()
        XCTAssertEqual(model.phase, .signedOut)
        XCTAssertEqual(parts.mock.requests.last?.url.path, "/api/auth/logout-all")
        XCTAssertEqual(parts.mock.requests.last?.body, Data("{}".utf8))
        XCTAssertNil(try parts.store.loadSession())
    }

    @MainActor
    func testVerifierExpiresAtExactly900Seconds() async throws {
        let start = Date(timeIntervalSince1970: 1_700_000_000)
        let clock = TestClock(start)
        let parts = makeClient(bytes: contractVerifierBytes, now: { clock.date })
        let model = AuthModel(client: parts.client, deviceLabel: "iPhone")
        model.emailDraft = "singer@example.com"
        await model.requestLink()
        XCTAssertEqual(model.phase, .checkEmail)
        XCTAssertEqual(AuthTiming.verifierLifetime, 900)

        clock.date = start.addingTimeInterval(899)
        model.refreshPendingLink()
        XCTAssertEqual(model.phase, .checkEmail)
        XCTAssertNotNil(try parts.store.loadVerifier())

        clock.date = start.addingTimeInterval(900)
        let before = parts.mock.requests.count
        do {
            _ = try await parts.client.verify(token: loginToken, deviceLabel: "iPhone")
            XCTFail("an expired verifier must not call verify")
        } catch AuthError.missingVerifier {
        }
        XCTAssertEqual(parts.mock.requests.count, before)
        XCTAssertNil(try parts.store.loadSession())
        XCTAssertNil(try parts.store.loadVerifier())
        model.refreshPendingLink()
        XCTAssertEqual(model.phase, .signedOut)
        XCTAssertNil(model.statusText)
    }

    func testSessionTokenIsCheckedBeforeItIsStored() async throws {
        let parts = makeClient(bytes: contractVerifierBytes)
        try await parts.client.requestLink(email: "singer@example.com")
        parts.mock.handler = { _ in
            AuthHTTPResponse(status: 200, body: Data("{\"token\":\"short\"}".utf8))
        }
        do {
            _ = try await parts.client.verify(token: loginToken, deviceLabel: "iPhone")
            XCTFail("a short token must not be stored")
        } catch AuthError.missingToken {
        }
        XCTAssertNil(try parts.store.loadSession())
        XCTAssertFalse(String(describing: AuthError.missingToken).contains(sessionToken))

        let tooShort = String(repeating: "a", count: 42)
        let tooLong = String(repeating: "a", count: 129)
        let badChar = String(repeating: "a", count: 42) + "+"
        for bad in [tooShort, tooLong, badChar] {
            XCTAssertThrowsError(try parts.client.storeSession(bad))
            XCTAssertNil(try parts.store.loadSession())
        }
        let accepted = String(repeating: "c", count: 43)
        try parts.client.storeSession(accepted)
        XCTAssertEqual(try parts.store.loadSession(), accepted)
        let max = String(repeating: "d", count: 128)
        try parts.client.storeSession(max)
        XCTAssertEqual(try parts.store.loadSession(), max)
    }

    func testAuthenticatedRedirectsAreRefused() async throws {
        for status in [302, 307, 308] {
            let parts = makeClient()
            try parts.store.saveSession(sessionToken)
            parts.mock.handler = { _ in
                AuthHTTPResponse(status: status, body: Data())
            }
            do {
                _ = try await parts.client.currentEmail()
                XCTFail("status \(status)")
            } catch AuthError.redirectRefused {
            }
            XCTAssertEqual(parts.mock.requests.count, 1)
            XCTAssertEqual(parts.mock.requests[0].headers["authorization"], "Bearer \(sessionToken)")
            XCTAssertEqual(try parts.store.loadSession(), sessionToken)
            XCTAssertFalse(String(describing: AuthError.redirectRefused).contains(sessionToken))
        }
    }

    func testLogoutAllStatusCodes() async throws {
        try await assertLogoutAll(status: 401, code: "unauthorized", clears: true)
        try await assertLogoutAll(status: 403, code: "forbidden", clears: false)
        try await assertLogoutAll(status: 405, code: "method_not_allowed", clears: false)
    }

    @MainActor
    func testFailedSignOutEverywhereNamesThatAction() async throws {
        let parts = makeClient()
        try parts.store.saveSession(sessionToken)
        parts.mock.handler = { _ in
            AuthHTTPResponse(status: 403, body: Data("{\"error\":\"forbidden\"}".utf8))
        }
        let model = AuthModel(client: parts.client, deviceLabel: "iPhone")
        model.requestSignOutEverywhere()
        XCTAssertTrue(model.confirmSignOutEverywhere)
        XCTAssertTrue(parts.mock.requests.isEmpty)
        await model.signOutEverywhere()
        XCTAssertEqual(model.banner, "Could not sign out everywhere.")
        XCTAssertEqual(try parts.store.loadSession(), sessionToken)
        XCTAssertFalse(model.confirmSignOutEverywhere)
    }

    @MainActor
    func testDismissStopsAnInFlightVerifyFromSavingASession() async {
        let parts = makeClient(bytes: contractVerifierBytes)
        let hold = RequestHold()
        parts.mock.beforeResponse = { request in
            if request.url.path == "/api/auth/verify" {
                await hold.wait()
            }
        }
        parts.mock.handler = scripted
        let model = AuthModel(client: parts.client, deviceLabel: "iPhone")
        model.emailDraft = "singer@example.com"
        await model.requestLink()
        let task = Task {
            await model.open(url: URL(string: "softchord://login?token=\(loginToken)")!)
        }
        await waitFor(parts.mock, path: "/api/auth/verify")
        model.dismissSignIn()
        hold.release()
        await task.value
        XCTAssertNil(try? parts.store.loadSession())
        XCTAssertEqual(model.phase, .signedOut)
    }

    @MainActor
    func testLateMe401DoesNotClearANewerToken() async throws {
        let parts = makeClient()
        try parts.store.saveSession(sessionToken)
        let newer = String(repeating: "e", count: 43)
        let hold = RequestHold()
        parts.mock.beforeResponse = { request in
            if request.url.path == "/api/me" {
                await hold.wait()
            }
        }
        parts.mock.handler = { request in
            if request.url.path == "/api/me" {
                return AuthHTTPResponse(status: 401, body: Data("{\"error\":\"unauthorized\"}".utf8))
            }
            return AuthHTTPResponse(status: 200, body: Data("{\"ok\":true}".utf8))
        }
        let model = AuthModel(client: parts.client, deviceLabel: "iPhone")
        let loading = Task { await model.reloadAccount() }
        await waitFor(parts.mock, path: "/api/me")
        await model.signOut()
        try parts.store.saveSession(newer)
        hold.release()
        await loading.value
        XCTAssertEqual(try parts.store.loadSession(), newer)
        XCTAssertNotEqual(model.phase, .signedIn(email: "singer@example.com"))
    }

    @MainActor
    func testLateMe200AfterSignOutDoesNotShowTheEmail() async throws {
        let parts = makeClient()
        try parts.store.saveSession(sessionToken)
        let hold = RequestHold()
        parts.mock.beforeResponse = { request in
            if request.url.path == "/api/me" {
                await hold.wait()
            }
        }
        parts.mock.handler = { request in
            if request.url.path == "/api/me" {
                return AuthHTTPResponse(status: 200, body: Data("{\"email\":\"singer@example.com\"}".utf8))
            }
            return AuthHTTPResponse(status: 200, body: Data("{\"ok\":true}".utf8))
        }
        let model = AuthModel(client: parts.client, deviceLabel: "iPhone")
        let loading = Task { await model.reloadAccount() }
        await waitFor(parts.mock, path: "/api/me")
        await model.signOut()
        hold.release()
        await loading.value
        XCTAssertEqual(model.phase, .signedOut)
        XCTAssertNil(try parts.store.loadSession())
        XCTAssertNil(model.statusText)
    }

    @MainActor
    func testALinkThatArrivesWhileBusyIsNotDropped() async {
        let parts = makeClient(bytes: contractVerifierBytes)
        let hold = RequestHold()
        parts.mock.beforeResponse = { request in
            if request.url.path == "/api/auth/request-link" {
                await hold.wait()
            }
        }
        parts.mock.handler = scripted
        let model = AuthModel(client: parts.client, deviceLabel: "iPhone")
        model.emailDraft = "singer@example.com"
        let requesting = Task { await model.requestLink() }
        await waitFor(parts.mock, path: "/api/auth/request-link")
        await model.open(url: URL(string: "softchord://login?token=\(loginToken)")!)
        XCTAssertEqual(model.banner, AuthCopy.linkWaiting)
        XCTAssertFalse(parts.mock.requests.contains { $0.url.path == "/api/auth/verify" })
        hold.release()
        await requesting.value
        XCTAssertTrue(parts.mock.requests.contains { $0.url.path == "/api/auth/verify" })
        XCTAssertEqual(model.phase, .signedIn(email: "singer@example.com"))
    }

    @MainActor
    func testOldTokenMe401DoesNotWipeANewerSession() async throws {
        let parts = makeClient(bytes: contractVerifierBytes)
        try parts.store.saveSession(sessionToken)
        let newer = String(repeating: "f", count: 43)
        let holdVerify = RequestHold()
        let holdMe = RequestHold()
        parts.mock.beforeResponse = { request in
            if request.url.path == "/api/auth/verify" {
                await holdVerify.wait()
            } else if request.url.path == "/api/me" {
                await holdMe.wait()
            }
        }
        parts.mock.handler = { request in
            switch request.url.path {
            case "/api/auth/verify":
                let body = "{\"email\":\"singer@example.com\",\"token\":\"\(newer)\"}"
                return AuthHTTPResponse(status: 200, body: Data(body.utf8))
            case "/api/me":
                if request.headers["authorization"] == "Bearer \(sessionToken)" {
                    return AuthHTTPResponse(status: 401, body: Data("{\"error\":\"unauthorized\"}".utf8))
                }
                return AuthHTTPResponse(status: 200, body: Data("{\"email\":\"singer@example.com\"}".utf8))
            default:
                return AuthHTTPResponse(status: 200, body: Data("{\"ok\":true}".utf8))
            }
        }
        let model = AuthModel(client: parts.client, deviceLabel: "iPhone")
        model.emailDraft = "singer@example.com"
        await model.requestLink()
        let signingIn = Task {
            await model.open(url: URL(string: "softchord://login?token=\(loginToken)")!)
        }
        await waitFor(parts.mock, path: "/api/auth/verify")
        let reloading = Task { await model.reloadAccount() }
        await waitForCount(parts.mock, path: "/api/me", count: 1)
        holdVerify.release()
        await waitForCount(parts.mock, path: "/api/me", count: 2)
        XCTAssertEqual(try parts.store.loadSession(), newer)
        holdMe.release()
        await signingIn.value
        await reloading.value
        XCTAssertEqual(try parts.store.loadSession(), newer)
        XCTAssertEqual(model.phase, .signedIn(email: "singer@example.com"))
    }

    @MainActor
    func testSignOutDoesNotClearBusyWhileAnotherCallIsRunning() async throws {
        let parts = makeClient()
        try parts.store.saveSession(sessionToken)
        let hold = RequestHold()
        parts.mock.beforeResponse = { request in
            if request.url.path == "/api/me" {
                await hold.wait()
            }
        }
        parts.mock.handler = { request in
            if request.url.path == "/api/me" {
                return AuthHTTPResponse(status: 200, body: Data("{\"email\":\"singer@example.com\"}".utf8))
            }
            return AuthHTTPResponse(status: 200, body: Data("{\"ok\":true}".utf8))
        }
        let model = AuthModel(client: parts.client, deviceLabel: "iPhone")
        let loading = Task { await model.reloadAccount() }
        await waitFor(parts.mock, path: "/api/me")
        XCTAssertTrue(model.busy)
        await model.signOut()
        XCTAssertTrue(model.busy)
        hold.release()
        await loading.value
        XCTAssertFalse(model.busy)
        XCTAssertNil(try parts.store.loadSession())
    }

    private var songsOrigin: APIOrigin {
        APIOrigin.resolve("https://songs.example")
    }

    private func assertLogoutAll(status: Int, code: String, clears: Bool) async throws {
        let parts = makeClient()
        try parts.store.saveSession(sessionToken)
        parts.mock.handler = { _ in
            let body = "{\"error\":\"\(code)\"}"
            return AuthHTTPResponse(status: status, body: Data(body.utf8))
        }
        do {
            try await parts.client.logoutEverywhere()
            XCTAssertTrue(clears, "status \(status) should have failed")
        } catch let error as AuthError {
            XCTAssertEqual(error, .rejected(status: status, code: code))
            XCTAssertFalse(clears)
            XCTAssertFalse(String(describing: error).contains(sessionToken))
        }
        if clears {
            XCTAssertNil(try parts.store.loadSession())
        } else {
            XCTAssertEqual(try parts.store.loadSession(), sessionToken)
        }
    }

    private func waitFor(_ mock: MockAuthHTTP, path: String) async {
        await waitForCount(mock, path: path, count: 1)
    }

    private func waitForCount(_ mock: MockAuthHTTP, path: String, count: Int) async {
        for _ in 0..<50 {
            if mock.requests.filter({ $0.url.path == path }).count >= count {
                return
            }
            try? await Task.sleep(nanoseconds: 20_000_000)
        }
    }

    private func contractData() throws -> Data {
        let url = try XCTUnwrap(
            Bundle(for: AuthTests.self).url(forResource: "api-contract", withExtension: "json"),
            "api-contract.json is missing from the SoftChordTests bundle"
        )
        return try Data(contentsOf: url)
    }

    private func contractJSON() throws -> [String: Any] {
        try XCTUnwrap(JSONSerialization.jsonObject(with: try contractData()) as? [String: Any])
    }

    private func jsonObject(_ data: Data?) throws -> [String: Any] {
        try XCTUnwrap(JSONSerialization.jsonObject(with: try XCTUnwrap(data)) as? [String: Any])
    }

    private func makeClient(
        origin: String = "https://songs.example",
        bytes: Data? = nil,
        now: @escaping @Sendable () -> Date = { Date() }
    ) -> (client: AuthClient, mock: MockAuthHTTP, store: MemorySessionStore) {
        let mock = MockAuthHTTP()
        let store = MemorySessionStore()
        let client = AuthClient(
            originRaw: origin,
            transport: mock,
            store: store,
            randomBytes: {
                if let bytes {
                    return bytes
                }
                return Data(repeating: 7, count: 32)
            },
            now: now
        )
        return (client, mock, store)
    }

    private func scripted(_ request: CapturedAuthRequest) -> AuthHTTPResponse {
        switch request.url.path {
        case "/api/auth/verify":
            let body = "{\"email\":\"singer@example.com\",\"token\":\"\(sessionToken)\"}"
            return AuthHTTPResponse(status: 200, body: Data(body.utf8))
        case "/api/me":
            return AuthHTTPResponse(status: 200, body: Data("{\"email\":\"singer@example.com\"}".utf8))
        default:
            return AuthHTTPResponse(status: 200, body: Data("{\"ok\":true}".utf8))
        }
    }
}

private struct CapturedAuthRequest: Sendable {
    var method: String
    var url: URL
    var headers: [String: String]
    var body: Data?
    var onMainThread: Bool
    var timeout: TimeInterval

    var contentType: String? { headers["content-type"] }

    init(_ request: URLRequest) {
        method = request.httpMethod ?? ""
        url = request.url ?? URL(string: "https://invalid.example/")!
        var lowered: [String: String] = [:]
        for (key, value) in request.allHTTPHeaderFields ?? [:] {
            lowered[key.lowercased()] = value
        }
        headers = lowered
        body = request.httpBody
        onMainThread = Thread.isMainThread
        timeout = request.timeoutInterval
    }
}

private final class TestClock: @unchecked Sendable {
    var date: Date
    init(_ date: Date) { self.date = date }
}

private final class RequestHold: @unchecked Sendable {
    private let lock = NSLock()
    private var waiters: [CheckedContinuation<Void, Never>] = []

    func wait() async {
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            lock.lock()
            waiters.append(continuation)
            lock.unlock()
        }
    }

    func release() {
        lock.lock()
        let pending = waiters
        waiters.removeAll()
        lock.unlock()
        pending.forEach { $0.resume() }
    }
}

/// Returns 400 unless a POST's content type is exactly `application/json`.
private final class MockAuthHTTP: AuthHTTPSending, @unchecked Sendable {
    private let lock = NSLock()
    private var stored: [CapturedAuthRequest] = []
    var handler: (@Sendable (CapturedAuthRequest) -> AuthHTTPResponse)?
    var beforeResponse: (@Sendable (CapturedAuthRequest) async -> Void)?
    var transportError: Error?

    var requests: [CapturedAuthRequest] {
        lock.lock()
        defer { lock.unlock() }
        return stored
    }

    func removeAll() {
        lock.lock()
        stored.removeAll()
        lock.unlock()
    }

    func send(_ request: URLRequest) async throws -> AuthHTTPResponse {
        let captured = CapturedAuthRequest(request)
        lock.lock()
        stored.append(captured)
        let handler = self.handler
        let beforeResponse = self.beforeResponse
        let transportError = self.transportError
        lock.unlock()
        if let beforeResponse {
            await beforeResponse(captured)
        }
        if request.httpMethod == "POST", captured.contentType != "application/json" {
            return AuthHTTPResponse(status: 400, body: Data("{\"error\":\"invalid_request\"}".utf8))
        }
        if let transportError {
            throw transportError
        }
        if let handler {
            return handler(captured)
        }
        return AuthHTTPResponse(status: 200, body: Data("{\"ok\":true}".utf8))
    }
}

private final class MemorySessionStore: SessionStoring, @unchecked Sendable {
    private let lock = NSLock()
    private var session: String?
    private var verifier: String?
    private var verifierIssuedAt: Date?

    func saveSession(_ token: String) throws {
        lock.lock()
        session = token
        lock.unlock()
    }

    func loadSession() throws -> String? {
        lock.lock()
        defer { lock.unlock() }
        return session
    }

    func saveVerifier(_ value: String, issuedAt: Date) throws {
        lock.lock()
        verifier = value
        verifierIssuedAt = issuedAt
        lock.unlock()
    }

    func loadVerifier() throws -> String? {
        lock.lock()
        defer { lock.unlock() }
        return verifier
    }

    func loadVerifierIssuedAt() throws -> Date? {
        lock.lock()
        defer { lock.unlock() }
        return verifierIssuedAt
    }

    func clearVerifier() throws {
        lock.lock()
        verifier = nil
        verifierIssuedAt = nil
        lock.unlock()
    }

    func clear() throws {
        lock.lock()
        session = nil
        verifier = nil
        verifierIssuedAt = nil
        lock.unlock()
    }
}
