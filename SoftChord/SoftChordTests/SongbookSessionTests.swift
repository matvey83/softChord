import Foundation
import Testing
@testable import SoftChord

@Suite(.serialized)
struct SongbookSessionTests {
    @Test func displayNameDropsTheSongbookExtension() {
        #expect(SongbookSession.displayName(fromFileName: "opened-from-this-session.songbook")
            == "opened-from-this-session")
        #expect(SongbookSession.displayName(fromFileName: "Mine.SONGBOOK") == "Mine")
        #expect(SongbookSession.displayName(fromFileName: "notes") == "notes")
        #expect(SongbookSession.displayName(fromFileName: ".songbook") == ".songbook")
        #expect(SongbookSession.displayName(fromFileName: "") == "songbook")
    }

    @Test func theHeaderShowsTheOpenSongbookAndNotSaved() throws {
        let demo = try scratchSongbook(named: "zvuki_neba.songbook")
        defer { cleanup(demo) }
        let session = SongbookSession(demoName: "zvuki_neba", demoURL: demo, songs: nil)
        defer { Songbook.useBundledDemo() }
        #expect(session.displayName == "zvuki_neba")
        #expect(SongbookSession.indicator == "Not saved")
        #expect(session.entries.map(\.displayName) == ["zvuki_neba"])
        #expect(session.entries[0].id == session.currentId)
        #expect(session.songs.map(\.title) == ["Alpha", "beta Song"])
        #expect(session.loadError == nil)
    }

    @Test func notAvailableItemsUseTheSpecWording() {
        #expect(SongbookUnavailableItem.signIn.title == "Sign-in isn't available yet")
        #expect(SongbookUnavailableItem.signIn.message
            == "softChord accounts are coming in a later update.")
        #expect(SongbookUnavailableItem.share.title == "Sharing isn't available yet")
        #expect(SongbookUnavailableItem.share.message
            == "Sharing needs a softChord account, which is coming in a later update.")
        #expect(SongbookUnavailableItem.rename.title == "Not available yet")
        #expect(SongbookUnavailableItem.rename.message
            == "Renaming and deleting songbooks comes with softChord accounts in a later update.")
        #expect(SongbookUnavailableItem.delete.title == SongbookUnavailableItem.rename.title)
        #expect(SongbookUnavailableItem.delete.message == SongbookUnavailableItem.rename.message)
        #expect(SongbookUnavailableItem.saveCopy.title == "Not available yet")
        #expect(SongbookUnavailableItem.saveCopy.message
            == "Saving songbooks from this app is coming in a later update.")
        #expect(SongbookSession.openFromFilesTitle == "Open from Files\u{2026}")
        #expect(SongbookSession.saveCopyTitle == "Save a Copy to Files\u{2026}")
        #expect(SongbookSession.renameTitle == "Rename\u{2026}")
        #expect(SongbookSession.deleteTitle == "Delete\u{2026}")
        #expect(SongbookSession.shareTitle == "Share\u{2026}")
        #expect(SongbookSession.signInTitle == "Sign in")
        #expect(SongbookSession.mySongbooksTitle == "My songbooks")
    }

    @Test func openingAValidFileAddsItAndDropsTheExtension() throws {
        let demo = try scratchSongbook(named: "zvuki_neba.songbook")
        let opened = try scratchSongbook(named: "opened-from-this-session.songbook")
        defer { cleanup(demo); cleanup(opened) }
        var session = SongbookSession(demoName: "zvuki_neba", demoURL: demo, songs: nil)
        defer { Songbook.useBundledDemo() }
        let openedFailure = session.openPickedFile(opened)
        #expect(openedFailure == nil)
        #expect(session.displayName == "opened-from-this-session")
        #expect(session.entries.map(\.displayName) == ["zvuki_neba", "opened-from-this-session"])
        #expect(session.current?.id == session.entries[1].id)
        #expect(session.songs.map(\.title) == ["Alpha", "beta Song"])
        let current = try Songbook.current
        #expect(current.displayName == "opened-from-this-session")
    }

    @Test func anInvalidFileKeepsTheCurrentSongbook() throws {
        let demo = try scratchSongbook(named: "zvuki_neba.songbook")
        let invalid = FileManager.default.temporaryDirectory
            .appendingPathComponent("notes-\(UUID().uuidString).songbook")
        try Data("this is not a songbook\n".utf8).write(to: invalid)
        defer { cleanup(demo); cleanup(invalid) }
        var session = SongbookSession(demoName: "zvuki_neba", demoURL: demo, songs: nil)
        defer { Songbook.useBundledDemo() }
        let failure = session.openPickedFile(invalid)
        #expect(failure?.title == "Can't open songbook")
        #expect(failure?.message == "\u{201C}\(invalid.lastPathComponent)\u{201D} isn't a softChord songbook.")
        #expect(session.displayName == "zvuki_neba")
        #expect(session.entries.count == 1)
    }

    @Test func aWrongFormatKeepsTheCurrentSongbook() throws {
        let demo = try scratchSongbook(named: "zvuki_neba.songbook")
        let older = try scratchSongbook(named: "older.songbook", version: 0)
        let newer = try scratchSongbook(named: "newer.songbook", version: 3)
        defer { cleanup(demo); cleanup(older); cleanup(newer) }
        var session = SongbookSession(demoName: "zvuki_neba", demoURL: demo, songs: nil)
        defer { Songbook.useBundledDemo() }

        let oldFailure = session.openPickedFile(older)
        #expect(oldFailure?.title == "Can't open songbook")
        #expect(oldFailure?.message == SongbookError.oldFormat.description)
        #expect(session.displayName == "zvuki_neba")

        let newFailure = session.openPickedFile(newer)
        #expect(newFailure?.title == "Can't open songbook")
        #expect(newFailure?.message == SongbookError.newerFormat(3).description)
        #expect(session.displayName == "zvuki_neba")
        #expect(session.entries.count == 1)
    }

    @Test func aFileOver50MBIsRefusedBeforeItIsRead() throws {
        #expect(!SongbookSession.isTooLarge(Int64(SongbookSession.maxBytes)))
        #expect(SongbookSession.isTooLarge(Int64(SongbookSession.maxBytes) + 1))

        let demo = try scratchSongbook(named: "zvuki_neba.songbook")
        let huge = try scratchSongbook(named: "huge.songbook")
        defer { cleanup(demo); cleanup(huge) }
        var session = SongbookSession(demoName: "zvuki_neba", demoURL: demo, songs: nil)
        defer { Songbook.useBundledDemo() }
        let failure = session.openPickedFile(
            huge,
            reportedSize: Int64(SongbookSession.maxBytes) + 1,
            downloadingStatus: nil,
            isUbiquitous: nil)
        #expect(failure == .tooLarge)
        #expect(failure?.message
            == "This songbook is too large to open here. Open it in softChord on your computer.")
        #expect(failure?.title == "Can't open songbook")
        #expect(session.displayName == "zvuki_neba")
        #expect(session.entries.count == 1)
    }

    @Test func anICloudFileThatIsNotDownloadedIsRefused() throws {
        let demo = try scratchSongbook(named: "zvuki_neba.songbook")
        let cloud = try scratchSongbook(named: "icloud.songbook")
        defer { cleanup(demo); cleanup(cloud) }
        var session = SongbookSession(demoName: "zvuki_neba", demoURL: demo, songs: nil)
        defer { Songbook.useBundledDemo() }
        let failure = session.openPickedFile(
            cloud,
            reportedSize: 100,
            downloadingStatus: .notDownloaded,
            isUbiquitous: true)
        #expect(failure == .notDownloaded)
        #expect(failure?.message == "This file isn't downloaded yet. Try again when you're online.")
        #expect(session.displayName == "zvuki_neba")
    }

    /// Switching or opening while a song has unsaved edits uses the same
    /// Save / Don't Save / Cancel prompt. Cancel keeps this songbook. A failed
    /// open after Don't Save also keeps it, and does not drop session edits.
    @Test func switchingOrOpeningWhileDirtyAsksAndCancelStays() throws {
        let demo = try scratchSongbook(named: "zvuki_neba.songbook")
        let other = try scratchSongbook(named: "other.songbook")
        let invalid = FileManager.default.temporaryDirectory
            .appendingPathComponent("notes-\(UUID().uuidString).songbook")
        try Data("not a database".utf8).write(to: invalid)
        defer { cleanup(demo); cleanup(other); cleanup(invalid) }

        var session = SongbookSession(demoName: "zvuki_neba", demoURL: demo, songs: nil)
        defer {
            Songbook.useBundledDemo()
            SongSessionEdits.reset()
        }
        let songId = try #require(session.songs.first?.id)
        SongSessionEdits.save(id: songId, text: "unsaved", chords: nil, steps: 1)
        let demoId = session.currentId

        #expect(session.request(.switchTo(demoId), dirty: true) == .ignore)
        #expect(session.request(.openFile, dirty: true) == .askToLeave(.openFile))
        #expect(session.displayName == "zvuki_neba")
        #expect(SongSessionEdits.copy(for: songId)?.text == "unsaved")

        // Don't Save, then an invalid file: the current songbook and the
        // session edit stay, because no songbook was opened.
        #expect(session.request(.openFile, dirty: false) == .proceed(.openFile))
        let failed = session.openPickedFile(invalid)
        #expect(failed?.message == "\u{201C}\(invalid.lastPathComponent)\u{201D} isn't a softChord songbook.")
        #expect(session.displayName == "zvuki_neba")
        #expect(SongSessionEdits.copy(for: songId)?.text == "unsaved")

        let openedOther = session.openPickedFile(other)
        #expect(openedOther == nil)
        #expect(session.displayName == "other")
        #expect(SongSessionEdits.copy(for: songId) == nil)
        #expect(session.entries.map(\.displayName) == ["zvuki_neba", "other"])

        #expect(session.request(.switchTo(demoId), dirty: true) == .askToLeave(.switchTo(demoId)))
        #expect(session.displayName == "other")

        #expect(session.request(.switchTo(demoId), dirty: false) == .proceed(.switchTo(demoId)))
        let switched = session.activate(id: demoId)
        #expect(switched)
        #expect(session.displayName == "zvuki_neba")
        #expect(SongSessionEdits.copy(for: songId) == nil)
    }
}

private func scratchSongbook(named name: String, version: Int = 2) throws -> URL {
    let directory = FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString, isDirectory: true)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let url = directory.appendingPathComponent(name)
    try writeSongbook(at: url, version: version)
    return url
}

private func cleanup(_ url: URL) {
    try? FileManager.default.setAttributes([.posixPermissions: 0o644], ofItemAtPath: url.path)
    try? FileManager.default.removeItem(at: url)
    try? FileManager.default.removeItem(at: url.deletingLastPathComponent())
}
