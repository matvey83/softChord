//
//  SongbookSession.swift
//  SoftChord
//
//  Phase 1 songbook header and menu: the open file for this launch, My
//  songbooks, Open from Files, and the not-available messages. Nothing is
//  written to the original file, and no network call is made.
//

import Foundation
import UniformTypeIdentifiers

/// One row under My songbooks: the bundled demo or a file opened this launch.
nonisolated struct SongbookSessionEntry: Equatable, Identifiable {
    let id: UUID
    var displayName: String
    var url: URL
    var isBundledDemo: Bool
}

/// Sign in and the account-only menu items. One OK button, no network call.
nonisolated enum SongbookUnavailableItem: Equatable, CaseIterable {
    case signIn
    case saveCopy
    case rename
    case delete
    case share

    var title: String {
        switch self {
        case .signIn:
            return "Sign-in isn't available yet"
        case .share:
            return "Sharing isn't available yet"
        case .saveCopy, .rename, .delete:
            return "Not available yet"
        }
    }

    var message: String {
        switch self {
        case .signIn:
            return "softChord accounts are coming in a later update."
        case .share:
            return "Sharing needs a softChord account, which is coming in a later update."
        case .rename, .delete:
            return "Renaming and deleting songbooks comes with softChord accounts in a later update."
        case .saveCopy:
            return "Saving songbooks from this app is coming in a later update."
        }
    }
}

/// Why a picked file did not open. The current songbook stays as it is.
nonisolated enum SongbookOpenFailure: Equatable {
    case tooLarge
    case notASongbook(fileName: String)
    case format(String)
    case cantRead
    case notDownloaded

    var title: String { "Can't open songbook" }

    var message: String {
        switch self {
        case .tooLarge:
            return "This songbook is too large to open here. Open it in softChord on your computer."
        case .notASongbook(let fileName):
            return "\u{201C}\(fileName)\u{201D} isn't a softChord songbook."
        case .format(let message):
            return message
        case .cantRead:
            return "softChord can't read this file."
        case .notDownloaded:
            return "This file isn't downloaded yet. Try again when you're online."
        }
    }
}

/// Switching My songbooks or choosing Open from Files….
nonisolated enum SongbookChangeRequest: Equatable {
    case switchTo(UUID)
    case openFile
}

nonisolated enum SongbookChangeDecision: Equatable {
    /// The open songbook is already the one that was chosen.
    case ignore
    /// Go ahead: switch, or present the file picker.
    case proceed(SongbookChangeRequest)
    /// The open song has unsaved edits. Show Save / Don't Save / Cancel first.
    case askToLeave(SongbookChangeRequest)
}

/// Holds Open from Files… chosen on the song list's leave alert until that
/// alert is no longer presented, so the file picker is not presented in the
/// same turn the alert dismisses. A switch needs no picker and goes ahead at
/// once. Cancel, or the system dismissing the alert, never opens the picker.
nonisolated struct SongbookImporterGate: Equatable {
    /// Open from Files… is waiting for the leave alert to go.
    private(set) var waitingForAlert = false

    /// Save or Don't Save was chosen on the leave alert. Returns the change to
    /// perform now, or nil when it waits for `alertDismissed()`.
    mutating func resolved(_ change: SongbookChangeRequest) -> SongbookChangeRequest? {
        switch change {
        case .switchTo:
            return change
        case .openFile:
            waitingForAlert = true
            return nil
        }
    }

    /// The leave alert is no longer presented. True, once, when the file
    /// picker should be presented now.
    mutating func alertDismissed() -> Bool {
        defer { waitingForAlert = false }
        return waitingForAlert
    }

    /// What Save / Don't Save should do next. Always calls `resolved` before
    /// treating the alert as gone, so an `onChange` that ran early (the
    /// isPresented binding can clear the alert before the button action)
    /// does not drop a waiting Open from Files….
    mutating func next(
        after change: SongbookChangeRequest, alertAlreadyGone: Bool
    ) -> SongbookImporterNext? {
        if let now = resolved(change) {
            return .perform(now)
        }
        if alertAlreadyGone {
            _ = alertDismissed()
            return .presentImporter
        }
        return nil
    }
}

/// The next step after Save or Don't Save on the song list's leave alert.
nonisolated enum SongbookImporterNext: Equatable {
    /// A songbook switch, which can run at once.
    case perform(SongbookChangeRequest)
    /// Present the file picker after the leave alert is gone.
    case presentImporter
}

/// The songbooks available this launch and the one that is open.
nonisolated struct SongbookSession: Equatable {
    /// Over 50 MB (1024-based) is refused before the file is copied or read.
    static let maxBytes = 50 * 1024 * 1024
    static let indicator = "Not saved"
    static let signInTitle = "Sign in"
    static let mySongbooksTitle = "My songbooks"
    static let openFromFilesTitle = "Open from Files\u{2026}"
    static let saveCopyTitle = "Save a Copy to Files\u{2026}"
    static let renameTitle = "Rename\u{2026}"
    static let deleteTitle = "Delete\u{2026}"
    static let shareTitle = "Share\u{2026}"

    var entries: [SongbookSessionEntry]
    var currentId: UUID
    var songs: [SongTitle]
    var loadError: String?

    var current: SongbookSessionEntry? {
        entries.first { $0.id == currentId } ?? entries.first
    }

    var displayName: String {
        current?.displayName ?? Songbook.demoResourceName
    }

    /// The .songbook type if the system knows it, otherwise a generic data type
    /// so the file picker still opens. The app is not registered as a document
    /// handler for the extension (that is later).
    static var songbookContentType: UTType {
        UTType(filenameExtension: "songbook") ?? .data
    }

    static var temporaryDirectory: URL {
        FileManager.default.temporaryDirectory.appendingPathComponent(
            "softchord-session", isDirectory: true)
    }

    /// Drop leftover copies from a previous launch. Call once at start, before
    /// any session file is opened.
    static func removeTemporaryFiles() {
        try? FileManager.default.removeItem(at: temporaryDirectory)
    }

    /// The name shown in the header and My songbooks: a trailing ".songbook"
    /// is dropped. The original name is kept only when that would leave it empty.
    static func displayName(fromFileName name: String) -> String {
        let stripped = name.replacingOccurrences(
            of: "\\.songbook$", with: "", options: [.regularExpression, .caseInsensitive])
        if stripped.isEmpty {
            return name.isEmpty ? "songbook" : name
        }
        return stripped
    }

    static func isTooLarge(_ byteCount: Int64) -> Bool {
        byteCount > Int64(maxBytes)
    }

    /// The bundled demo, already open.
    init() {
        do {
            let songbook = try Songbook.current
            self.init(demoName: songbook.displayName, demoURL: songbook.url, songs: nil)
        } catch {
            self.init(loadError: String(describing: error))
        }
    }

    init(loadError: String) {
        entries = []
        currentId = UUID()
        songs = []
        self.loadError = loadError
    }

    /// A session that starts on a known file, for the app and for tests.
    init(demoName: String, demoURL: URL, songs: [SongTitle]?) {
        let entry = SongbookSessionEntry(
            id: UUID(), displayName: demoName, url: demoURL, isBundledDemo: true)
        entries = [entry]
        currentId = entry.id
        if let songs {
            self.songs = songs
            loadError = nil
        } else {
            do {
                self.songs = try Songbook.titles(in: demoURL)
                loadError = nil
            } catch {
                self.songs = []
                loadError = String(describing: error)
            }
        }
    }

    /// Cancel keeps this songbook. Save and Don't Save continue with `change`.
    /// Choosing the songbook that is already open does nothing.
    func request(_ change: SongbookChangeRequest, dirty: Bool) -> SongbookChangeDecision {
        if case .switchTo(let id) = change, id == currentId {
            return .ignore
        }
        if SongLeavePrompt.shouldAsk(dirty: dirty) {
            return .askToLeave(change)
        }
        return .proceed(change)
    }

    /// Open a different songbook already in My songbooks. Session edits from
    /// the previous one are dropped. Returns false if the id is unknown.
    @discardableResult
    mutating func activate(id: UUID) -> Bool {
        guard let entry = entries.first(where: { $0.id == id }) else {
            return false
        }
        apply(entry)
        return true
    }

    /// Copy a picked file into a temp file, read it, and add it under My
    /// songbooks. On any failure the current songbook and its session edits stay.
    mutating func openPickedFile(_ url: URL) -> SongbookOpenFailure? {
        openPickedFile(url, reportedSize: nil, downloadingStatus: nil, isUbiquitous: nil)
    }

    /// The same as `openPickedFile(_:)`, with values tests can supply so a
    /// huge file or an iCloud placeholder does not have to be created.
    mutating func openPickedFile(
        _ url: URL,
        reportedSize: Int64?,
        downloadingStatus: URLUbiquitousItemDownloadingStatus?,
        isUbiquitous: Bool?
    ) -> SongbookOpenFailure? {
        let fileName = url.lastPathComponent
        if let failure = Self.preflightFailure(
            url: url,
            fileName: fileName,
            reportedSize: reportedSize,
            downloadingStatus: downloadingStatus,
            isUbiquitous: isUbiquitous
        ) {
            return failure
        }

        let accessed = url.startAccessingSecurityScopedResource()
        defer {
            if accessed {
                url.stopAccessingSecurityScopedResource()
            }
        }

        if let failure = Self.preflightFailure(
            url: url,
            fileName: fileName,
            reportedSize: reportedSize,
            downloadingStatus: downloadingStatus,
            isUbiquitous: isUbiquitous
        ) {
            return failure
        }

        let dest: URL
        do {
            dest = try Self.copyToTemporaryFile(url)
        } catch {
            return Self.openFailure(from: error, fileName: fileName, url: url)
        }

        do {
            let titles = try Songbook.titles(in: dest)
            let entry = SongbookSessionEntry(
                id: UUID(),
                displayName: Self.displayName(fromFileName: fileName),
                url: dest,
                isBundledDemo: false)
            entries.append(entry)
            songs = titles
            loadError = nil
            currentId = entry.id
            Songbook.setCurrent(CurrentSongbook(displayName: entry.displayName, url: entry.url))
            SongSessionEdits.reset()
            return nil
        } catch {
            Self.removeTemporaryFile(dest)
            return Self.openFailure(from: error, fileName: fileName, url: url)
        }
    }

    /// Inspect a file before it is copied. Tests pass size and iCloud status
    /// so those cases do not need a 50 MB file or a real iCloud item.
    static func preflightFailure(
        url: URL,
        fileName: String,
        reportedSize: Int64?,
        downloadingStatus: URLUbiquitousItemDownloadingStatus?,
        isUbiquitous: Bool?
    ) -> SongbookOpenFailure? {
        let values = try? url.resourceValues(forKeys: [
            .fileSizeKey,
            .isUbiquitousItemKey,
            .ubiquitousItemDownloadingStatusKey,
        ])
        let ubiquitous = isUbiquitous ?? values?.isUbiquitousItem ?? false
        let status = downloadingStatus ?? values?.ubiquitousItemDownloadingStatus
        if ubiquitous, let status, status != .current {
            return .notDownloaded
        }
        let size = reportedSize ?? values?.fileSize.map(Int64.init)
        if let size, isTooLarge(size) {
            return .tooLarge
        }
        return nil
    }

    /// What to show when the file picker reports an error. Cancelling the
    /// picker (NSUserCancelledError) shows nothing; anything else is cantRead.
    static func pickerFailure(_ error: Error) -> SongbookOpenFailure? {
        let nsError = error as NSError
        if nsError.domain == NSCocoaErrorDomain && nsError.code == NSUserCancelledError {
            return nil
        }
        return .cantRead
    }

    static func openFailure(from error: Error, fileName: String, url: URL) -> SongbookOpenFailure {
        let nsError = error as NSError
        if nsError.domain == NSCocoaErrorDomain {
            if nsError.code == NSFileReadNoPermissionError
                || nsError.code == NSFileReadNoSuchFileError
            {
                if (try? url.resourceValues(forKeys: [.isUbiquitousItemKey]))?.isUbiquitousItem == true {
                    return .notDownloaded
                }
            }
            if nsError.code == NSFileReadNoPermissionError {
                return .cantRead
            }
        }
        if let songbookError = error as? SongbookError {
            switch songbookError {
            case .oldFormat, .newerFormat:
                return .format(songbookError.description)
            default:
                return .notASongbook(fileName: fileName)
            }
        }
        return .notASongbook(fileName: fileName)
    }

    private mutating func apply(_ entry: SongbookSessionEntry) {
        currentId = entry.id
        // Always go through setCurrent so titles and the open song read this
        // URL, including when switching back to the demo.
        Songbook.setCurrent(CurrentSongbook(displayName: entry.displayName, url: entry.url))
        SongSessionEdits.reset()
        do {
            songs = try Songbook.titles(in: entry.url)
            loadError = nil
        } catch {
            songs = []
            loadError = String(describing: error)
        }
    }

    private static func copyToTemporaryFile(_ url: URL) throws -> URL {
        let directory = temporaryDirectory
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let dest = directory.appendingPathComponent("\(UUID().uuidString).songbook")
        try FileManager.default.copyItem(at: url, to: dest)
        try FileManager.default.setAttributes(
            [.posixPermissions: 0o444], ofItemAtPath: dest.path)
        return dest
    }

    private static func removeTemporaryFile(_ url: URL) {
        try? FileManager.default.setAttributes(
            [.posixPermissions: 0o644], ofItemAtPath: url.path)
        try? FileManager.default.removeItem(at: url)
    }
}
