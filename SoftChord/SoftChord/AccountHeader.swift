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
                auth.dismissSignIn()
            }
            Button(AuthCopy.cancel) {
                auth.dismissSignIn()
            }
        }
        .onAppear { auth.refreshPendingLink() }
        .task(id: auth.phase) {
            guard case .checkEmail = auth.phase else {
                return
            }
            while !Task.isCancelled {
                let wait = auth.pendingLinkRemaining()
                if wait <= 0 {
                    auth.refreshPendingLink()
                    return
                }
                do {
                    let nanos = max(UInt64(1_000_000), UInt64((wait * 1_000_000_000).rounded()))
                    try await Task.sleep(nanoseconds: nanos)
                } catch {
                    return
                }
                auth.refreshPendingLink()
            }
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
                    auth.requestSignOutEverywhere()
                }
            }
        }
        .confirmationDialog(
            AuthCopy.signOutEverywherePrompt,
            isPresented: $auth.confirmSignOutEverywhere,
            titleVisibility: .visible
        ) {
            Button(AuthCopy.signOutEverywhere, role: .destructive) {
                Task { await auth.signOutEverywhere() }
            }
            Button(AuthCopy.cancel, role: .cancel) {}
        }
    }

    private func actionButton(_ title: String, action: @escaping @MainActor () async -> Void) -> some View {
        Button(title) {
            Task { await action() }
        }
        .disabled(auth.busy)
    }
}
