//
//  SoftChordApp.swift
//  SoftChord
//
//  Created by Matvey Adzhigirey on 10/21/26.
//

import SwiftUI

@main
struct SoftChordApp: App {
    init() {
        // Session copies of files opened last launch do not survive a relaunch.
        SongbookSession.removeTemporaryFiles()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
