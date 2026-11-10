//
//  SessionStore.swift
//  SoftChord
//

import Foundation
import Security

/// The session token and the verifier that binds the magic link to this device.
nonisolated protocol SessionStoring: Sendable {
    func saveSession(_ token: String) throws
    func loadSession() throws -> String?
    func saveVerifier(_ value: String, issuedAt: Date) throws
    func loadVerifier() throws -> String?
    func loadVerifierIssuedAt() throws -> Date?
    func clearVerifier() throws
    func clear() throws
}

/// Keychain items stay on this device. They are not synced through iCloud Keychain.
nonisolated final class KeychainSessionStore: SessionStoring, @unchecked Sendable {
    static let service = "com.matveygirey.softChord-Viewer.auth"

    private let sessionAccount = "session"
    private let verifierAccount = "verifier"

    func saveSession(_ token: String) throws {
        try write(token, account: sessionAccount)
    }

    func loadSession() throws -> String? {
        try read(account: sessionAccount)
    }

    func saveVerifier(_ value: String, issuedAt: Date) throws {
        let millis = Int64((issuedAt.timeIntervalSince1970 * 1000).rounded())
        try write("\(millis)\n\(value)", account: verifierAccount)
    }

    func loadVerifier() throws -> String? {
        try pending()?.value
    }

    func loadVerifierIssuedAt() throws -> Date? {
        try pending()?.issuedAt
    }

    private func pending() throws -> (value: String, issuedAt: Date)? {
        guard let raw = try read(account: verifierAccount),
              let split = raw.firstIndex(of: "\n"),
              let millis = Int64(raw[..<split])
        else {
            return nil
        }
        let value = String(raw[raw.index(after: split)...])
        return (value, Date(timeIntervalSince1970: Double(millis) / 1000))
    }

    func clearVerifier() throws {
        try delete(account: verifierAccount)
    }

    func clear() throws {
        try delete(account: sessionAccount)
        try delete(account: verifierAccount)
    }

    private func write(_ value: String, account: String) throws {
        try delete(account: account)
        var query = baseQuery(account: account)
        query[kSecValueData as String] = Data(value.utf8)
        query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw AuthError.storage
        }
    }

    private func read(account: String) throws -> String? {
        var query = baseQuery(account: account)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        if status == errSecItemNotFound {
            return nil
        }
        guard status == errSecSuccess, let data = item as? Data, let string = String(data: data, encoding: .utf8) else {
            throw AuthError.storage
        }
        return string
    }

    private func delete(account: String) throws {
        let status = SecItemDelete(baseQuery(account: account) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw AuthError.storage
        }
    }

    private func baseQuery(account: String) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Self.service,
            kSecAttrAccount as String: account,
        ]
    }
}
