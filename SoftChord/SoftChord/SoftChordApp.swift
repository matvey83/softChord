//
//  SoftChordApp.swift
//  SoftChord
//
//  Created by Matvey Adzhigirey on 10/21/26.
//

import SwiftUI

@main
struct SoftChordApp: App {
    @ObservedObject private var auth = AuthModel.shared

    var body: some Scene {
        WindowGroup {
            ContentView(auth: auth)
                .onOpenURL { url in
                    Task { await auth.open(url: url) }
                }
        }
    }
}
