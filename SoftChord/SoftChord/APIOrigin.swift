//
//  APIOrigin.swift
//  SoftChord
//

import Foundation

/// Where sign-in calls go. An empty plist value is not configured.
nonisolated enum APIOrigin: Equatable, Sendable {
    case notConfigured
    case needsHTTPS
    case allowed(URL)

    static let plistKey = "SoftChordAPIOrigin"

    static func plistValue(bundle: Bundle = .main) -> String {
        (bundle.object(forInfoDictionaryKey: plistKey) as? String) ?? ""
    }

    /// `https` is allowed. `http` is allowed only for `localhost` and `127.0.0.1`.
    /// A path, user, query, or fragment is not an origin.
    static func resolve(_ raw: String?) -> APIOrigin {
        let trimmed = (raw ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            return .notConfigured
        }
        guard let parts = URLComponents(string: trimmed),
              let scheme = parts.scheme?.lowercased(),
              let host = parts.host?.lowercased(),
              !host.isEmpty,
              parts.user == nil,
              parts.password == nil,
              parts.query == nil,
              parts.fragment == nil,
              parts.path.isEmpty || parts.path == "/",
              let url = parts.url
        else {
            return .notConfigured
        }
        let local = host == "localhost" || host == "127.0.0.1"
        if scheme == "https" || (scheme == "http" && local) {
            return .allowed(url)
        }
        if scheme == "http" {
            return .needsHTTPS
        }
        return .notConfigured
    }
}
