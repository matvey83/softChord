//
//  AuthVerifier.swift
//  SoftChord
//

import CryptoKit
import Foundation
import Security

/// 32 random bytes, base64url, and the hex SHA-256 of that string.
nonisolated struct AuthVerifierMaterial: Equatable {
    var value: String
    var hash: String
}

nonisolated enum AuthVerifier {
    static func make(bytes: Data) throws -> AuthVerifierMaterial {
        guard bytes.count == 32 else {
            throw AuthError.storage
        }
        let value = base64URL(bytes)
        guard isVerifier(value) else {
            throw AuthError.storage
        }
        return AuthVerifierMaterial(value: value, hash: sha256Hex(Data(value.utf8)))
    }

    static func randomBytes() throws -> Data {
        var bytes = [UInt8](repeating: 0, count: 32)
        let status = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        guard status == errSecSuccess else {
            throw AuthError.storage
        }
        return Data(bytes)
    }

    static func sha256Hex(_ data: Data) -> String {
        SHA256.hash(data: data).map { byte in
            let text = String(byte, radix: 16)
            return byte < 16 ? "0\(text)" : text
        }.joined()
    }

    static func base64URL(_ data: Data) -> String {
        data.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }

    /// The server's verifier syntax: 43 to 128 characters of base64url.
    static func isVerifier(_ value: String) -> Bool {
        guard (43...128).contains(value.count) else {
            return false
        }
        return value.unicodeScalars.allSatisfy { scalar in
            (scalar >= "A" && scalar <= "Z")
                || (scalar >= "a" && scalar <= "z")
                || (scalar >= "0" && scalar <= "9")
                || scalar == "-"
                || scalar == "_"
        }
    }

    /// The server's bearer syntax. A session token is 32 bytes of base64url.
    static func isSessionToken(_ value: String) -> Bool {
        isVerifier(value)
    }
}
