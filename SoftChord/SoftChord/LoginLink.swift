//
//  LoginLink.swift
//  SoftChord
//

import Foundation

/// A link the app was asked to open.
nonisolated enum LoginLinkResult: Equatable {
    /// Not a sign-in link.
    case ignore
    /// Looks like sign-in, but the token is missing or not usable.
    case invalid
    case token(String)
}

/// `softchord://login?token=` and `https://<origin>/login#t=<token>`.
nonisolated enum LoginLink {
    static func classify(_ url: URL, origin: APIOrigin) -> LoginLinkResult {
        guard let parts = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let scheme = parts.scheme?.lowercased()
        else {
            return .ignore
        }
        switch scheme {
        case "softchord":
            return appLink(parts)
        case "https":
            return webLink(parts, allowCleartext: false, origin: origin)
        case "http":
            return webLink(parts, allowCleartext: true, origin: origin)
        default:
            return .ignore
        }
    }

    static func classify(pasted text: String, origin: APIOrigin) -> LoginLinkResult {
        var trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.hasPrefix("<"), trimmed.hasSuffix(">"), trimmed.count >= 2 {
            trimmed = String(trimmed.dropFirst().dropLast()).trimmingCharacters(in: .whitespacesAndNewlines)
        }
        guard let url = URL(string: trimmed) else {
            return .invalid
        }
        let result = classify(url, origin: origin)
        if case .ignore = result {
            return .invalid
        }
        return result
    }

    private static func appLink(_ parts: URLComponents) -> LoginLinkResult {
        guard parts.host?.lowercased() == "login" else {
            return .ignore
        }
        if !parts.path.isEmpty && parts.path != "/" {
            return .invalid
        }
        guard let token = parts.queryItems?.first(where: { $0.name == "token" })?.value else {
            return .invalid
        }
        guard let accepted = acceptable(token) else {
            return .invalid
        }
        return .token(accepted)
    }

    private static func webLink(_ parts: URLComponents, allowCleartext: Bool, origin: APIOrigin) -> LoginLinkResult {
        guard parts.path == "/login" || parts.path == "/login/" else {
            return .ignore
        }
        if parts.user != nil || parts.password != nil {
            return .invalid
        }
        let host = parts.host?.lowercased() ?? ""
        guard !host.isEmpty else {
            return .invalid
        }
        if allowCleartext && host != "localhost" && host != "127.0.0.1" {
            return .invalid
        }
        guard let fragment = parts.fragment, !fragment.isEmpty else {
            return .ignore
        }
        guard let token = fragmentToken(fragment), let accepted = acceptable(token) else {
            return .invalid
        }
        guard matches(parts, origin: origin) else {
            return .invalid
        }
        return .token(accepted)
    }

    /// A pasted or opened https link has to be the configured API origin.
    private static func matches(_ parts: URLComponents, origin: APIOrigin) -> Bool {
        guard case .allowed(let allowed) = origin,
              let allowedParts = URLComponents(url: allowed, resolvingAgainstBaseURL: false),
              parts.scheme?.lowercased() == allowedParts.scheme?.lowercased(),
              let host = parts.host?.lowercased(),
              host == allowedParts.host?.lowercased()
        else {
            return false
        }
        return port(parts) == port(allowedParts)
    }

    private static func port(_ parts: URLComponents) -> Int {
        if let port = parts.port {
            return port
        }
        switch parts.scheme?.lowercased() {
        case "https":
            return 443
        case "http":
            return 80
        default:
            return -1
        }
    }

    /// The fragment is `t=<token>`, the form the server builds.
    private static func fragmentToken(_ fragment: String) -> String? {
        guard let pieces = URLComponents(string: "https://parse.invalid/?\(fragment)") else {
            return nil
        }
        return pieces.queryItems?.first(where: { $0.name == "t" })?.value
    }

    /// The same base64url rule as a session token: 43 to 128 characters.
    private static func acceptable(_ token: String) -> String? {
        AuthVerifier.isVerifier(token) ? token : nil
    }
}
