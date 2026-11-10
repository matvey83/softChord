//
//  AccountHeader.swift
//  SoftChord
//

import SwiftUI

/// Sign in, above Search. The song list has no separate account menu.
struct AccountHeader: View {
    @ObservedObject var auth: AuthModel

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            switch auth.phase {
            case .notConfigured:
                Text(AuthCopy.notConfigured)
            case .needsHTTPS:
                Text(AuthCopy.needsHTTPS)
            case .signedOut:
                signedOut
            case .checkEmail:
                checkEmail
            case .signedIn(let email):
                signedIn(email)
            }
            if let banner = auth.banner {
                Text(banner)
                    .font(.footnote)
                    .foregroundStyle(.red)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var signedOut: some View {
        VStack(alignment: .leading, spacing: 6) {
            TextField("Email", text: $auth.emailDraft)
                .textFieldStyle(.roundedBorder)
                .keyboardType(.emailAddress)
                .textContentType(.emailAddress)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled(true)
                .disabled(auth.busy)
                .onSubmit { Task { await auth.requestLink() } }
            actionButton(AuthCopy.emailLink) { await auth.requestLink() }
        }
    }

    private var checkEmail: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(AuthCopy.checkEmail)
            TextField("Link", text: $auth.pastedLink)
                .textFieldStyle(.roundedBorder)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled(true)
                .disabled(auth.busy)
                .onSubmit { Task { await auth.open(pasted: auth.pastedLink) } }
            actionButton(AuthCopy.continueLink) { await auth.open(pasted: auth.pastedLink) }
            Button(AuthCopy.differentEmail) {
                auth.editEmailAgain()
            }
            .disabled(auth.busy)
        }
    }

    private func signedIn(_ email: String?) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(email ?? AuthCopy.signedIn)
                .lineLimit(1)
                .truncationMode(.middle)
            if email == nil {
                actionButton(AuthCopy.retry) { await auth.reloadAccount() }
            }
            HStack(spacing: 12) {
                actionButton(AuthCopy.signOut) { await auth.signOut() }
                Button(AuthCopy.signOutEverywhere, role: .destructive) {
                    Task { await auth.signOutEverywhere() }
                }
                .disabled(auth.busy)
            }
        }
    }

    private func actionButton(_ title: String, action: @escaping @MainActor () async -> Void) -> some View {
        Button(title) {
            Task { await action() }
        }
        .disabled(auth.busy)
    }
}
