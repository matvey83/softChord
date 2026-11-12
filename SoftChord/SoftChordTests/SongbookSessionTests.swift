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

    /// Cancelling the file picker shows nothing. Any other picker error is
    /// "softChord can't read this file."
    @Test func cancellingThePickerIsNotAFailure() {
        #expect(SongbookSession.pickerFailure(CocoaError(.userCancelled)) == nil)
        #expect(SongbookSession.pickerFailure(
            NSError(domain: NSCocoaErrorDomain, code: NSUserCancelledError)) == nil)
        #expect(SongbookSession.pickerFailure(
            NSError(domain: NSCocoaErrorDomain, code: NSFileReadNoPermissionError)) == .cantRead)
        #expect(SongbookSession.pickerFailure(
            NSError(domain: "other", code: NSUserCancelledError)) == .cantRead)
        #expect(SongbookSession.pickerFailure(URLError(.cancelled)) == .cantRead)
    }

    /// The song list's path (ContentView.requestChange and resolveLeave): a
    /// draft SongPage published as unsaved makes the request ask. Cancel stays
    /// and keeps the draft. Don't Save goes ahead but leaves the draft
    /// published until a songbook actually opens, so the list asks again if
    /// none did. Save keeps it for this run as Back's Save does, and the list
    /// does not ask again.
    @Test @MainActor func theListAsksAboutAnUnsavedDraftBeforeChanging() {
        SongSessionEdits.reset()
        defer { SongSessionEdits.reset() }
        let session = SongbookSession(
            demoName: "demo", demoURL: URL(fileURLWithPath: "/nonexistent.songbook"),
            songs: [SongTitle(id: 7, title: "Song")])
        let other = UUID()
        let source = SongSource(text: "Hello", chords: [SongChord.from(text: "C", characterNum: 0)])
        let draft = SongSessionEdits.UnsavedDraft(
            songId: 7, title: "Song",
            text: "Hello you", chords: [SongChord.from(text: "G", characterNum: 6)],
            steps: 2,
            startText: source.text, startChords: source.chords,
            source: source)
        func listRequest(_ change: SongbookChangeRequest) -> SongbookChangeDecision {
            session.request(change, dirty: SongSessionEdits.unsavedDraft != nil)
        }

        #expect(listRequest(.openFile) == .proceed(.openFile))

        // A clean page for another song does not drop the draft.
        SongSessionEdits.publish(draft, for: 7)
        SongSessionEdits.publish(nil, for: 8)
        #expect(SongSessionEdits.unsavedDraft == draft)
        #expect(listRequest(.switchTo(other)) == .askToLeave(.switchTo(other)))
        #expect(listRequest(.openFile) == .askToLeave(.openFile))

        // Cancel: stay, nothing saved, still asks next time.
        #expect(SongLeavePrompt.resolvingUnsavedDraft(.cancel, before: .openFile) == nil)
        #expect(SongSessionEdits.unsavedDraft == draft)
        #expect(SongSessionEdits.copy(for: 7) == nil)

        // Don't Save: go ahead, nothing saved. The draft stays published, so
        // with no songbook opened (picker cancelled) the list asks again.
        #expect(SongLeavePrompt.resolvingUnsavedDraft(.dontSave, before: .openFile) == .openFile)
        #expect(SongSessionEdits.unsavedDraft == draft)
        #expect(SongSessionEdits.copy(for: 7) == nil)
        #expect(listRequest(.openFile) == .askToLeave(.openFile))
        #expect(SongLeavePrompt.resolvingUnsavedDraft(.dontSave, before: .switchTo(other)) == .switchTo(other))
        #expect(SongSessionEdits.unsavedDraft == draft)
        #expect(listRequest(.switchTo(other)) == .askToLeave(.switchTo(other)))

        // A songbook opening drops it (activate and openPickedFile reset).
        SongSessionEdits.reset()
        #expect(SongSessionEdits.unsavedDraft == nil)
        #expect(listRequest(.openFile) == .proceed(.openFile))

        // Save: the draft is kept for this run, then the change goes ahead.
        SongSessionEdits.publish(draft, for: 7)
        #expect(SongLeavePrompt.resolvingUnsavedDraft(.save, before: .switchTo(other)) == .switchTo(other))
        #expect(SongSessionEdits.unsavedDraft == nil)
        #expect(SongSessionEdits.copy(for: 7) == SongSessionEdits.Copy(
            text: "Hello you", chords: draft.chords, steps: 2))
        #expect(listRequest(.switchTo(other)) == .proceed(.switchTo(other)))

        // The page clears its own draft once it is clean, and dropping the
        // session's edits clears it too.
        SongSessionEdits.publish(draft, for: 7)
        SongSessionEdits.publish(nil, for: 7)
        #expect(SongSessionEdits.unsavedDraft == nil)
        SongSessionEdits.publish(draft, for: 7)
        SongSessionEdits.reset()
        #expect(SongSessionEdits.unsavedDraft == nil)
    }

    /// Don't Save on the list, then a file that is not a songbook (or a
    /// cancelled picker, which opens nothing): the draft stays published and
    /// the list asks again. A file that opens drops it, as does a switch.
    /// Save, then a failed open: the session copy Save kept stays.
    @Test @MainActor func dontSaveKeepsTheDraftUntilASongbookOpens() throws {
        let demo = try scratchSongbook(named: "zvuki_neba.songbook")
        let other = try scratchSongbook(named: "other.songbook")
        let invalid = FileManager.default.temporaryDirectory
            .appendingPathComponent("notes-\(UUID().uuidString).songbook")
        try Data("not a database".utf8).write(to: invalid)
        defer { cleanup(demo); cleanup(other); cleanup(invalid) }
        SongSessionEdits.reset()
        var session = SongbookSession(demoName: "zvuki_neba", demoURL: demo, songs: nil)
        defer {
            Songbook.useBundledDemo()
            SongSessionEdits.reset()
        }
        let demoId = session.currentId
        let songId = try #require(session.songs.first?.id)
        let source = SongSource(text: "Hello", chords: [])
        let draft = SongSessionEdits.UnsavedDraft(
            songId: songId, title: "Alpha",
            text: "Hello you", chords: [], steps: 0,
            startText: source.text, startChords: source.chords,
            source: source)
        func listRequest(_ change: SongbookChangeRequest) -> SongbookChangeDecision {
            session.request(change, dirty: SongSessionEdits.unsavedDraft != nil)
        }

        // Don't Save, then the picker is cancelled: nothing opened.
        SongSessionEdits.publish(draft, for: songId)
        #expect(listRequest(.openFile) == .askToLeave(.openFile))
        #expect(SongLeavePrompt.resolvingUnsavedDraft(.dontSave, before: .openFile) == .openFile)
        #expect(SongbookSession.pickerFailure(CocoaError(.userCancelled)) == nil)
        #expect(SongSessionEdits.unsavedDraft == draft)
        #expect(listRequest(.openFile) == .askToLeave(.openFile))

        // Don't Save, then a bad file: still this songbook, draft still there.
        #expect(SongLeavePrompt.resolvingUnsavedDraft(.dontSave, before: .openFile) == .openFile)
        let invalidFailure = session.openPickedFile(invalid)
        #expect(invalidFailure != nil)
        #expect(session.displayName == "zvuki_neba")
        #expect(SongSessionEdits.unsavedDraft == draft)
        #expect(listRequest(.openFile) == .askToLeave(.openFile))

        // Don't Save, then a file that opens: the draft is dropped.
        #expect(SongLeavePrompt.resolvingUnsavedDraft(.dontSave, before: .openFile) == .openFile)
        let openedOther = session.openPickedFile(other)
        #expect(openedOther == nil)
        #expect(session.displayName == "other")
        #expect(SongSessionEdits.unsavedDraft == nil)
        #expect(SongSessionEdits.copy(for: songId) == nil)

        // Don't Save, then a switch: activate drops it.
        SongSessionEdits.publish(draft, for: songId)
        #expect(listRequest(.switchTo(demoId)) == .askToLeave(.switchTo(demoId)))
        #expect(SongLeavePrompt.resolvingUnsavedDraft(.dontSave, before: .switchTo(demoId))
            == .switchTo(demoId))
        #expect(SongSessionEdits.unsavedDraft == draft)
        let activated = session.activate(id: demoId)
        #expect(activated)
        #expect(session.displayName == "zvuki_neba")
        #expect(SongSessionEdits.unsavedDraft == nil)

        // Save, then a bad file: no longer unsaved, and the copy Save kept stays.
        SongSessionEdits.publish(draft, for: songId)
        #expect(SongLeavePrompt.resolvingUnsavedDraft(.save, before: .openFile) == .openFile)
        #expect(SongSessionEdits.unsavedDraft == nil)
        let invalidAfterSave = session.openPickedFile(invalid)
        #expect(invalidAfterSave != nil)
        #expect(SongSessionEdits.copy(for: songId)?.text == "Hello you")
        #expect(listRequest(.openFile) == .proceed(.openFile))
        // The switch then drops those session edits with the old songbook.
        let openedAfterSave = session.openPickedFile(other)
        #expect(openedAfterSave == nil)
        #expect(SongSessionEdits.copy(for: songId) == nil)
    }

    /// Open from Files… chosen on the leave alert waits for the alert to
    /// dismiss before the picker is presented; a switch goes ahead at once.
    /// Cancel, or the system dismissing the alert, never opens the picker.
    /// resolved(_:) is always applied before the alert is treated as gone, so
    /// an early onChange (isPresented binding before the button action) still
    /// presents the picker once.
    @Test func openFromTheLeaveAlertWaitsForItToDismiss() {
        let other = UUID()
        var gate = SongbookImporterGate()

        // Cancel or a system dismissal: nothing was resolved, nothing opens.
        let cancelled = gate.alertDismissed()
        #expect(!cancelled)

        let switched = gate.next(after: .switchTo(other), alertAlreadyGone: false)
        #expect(switched == .perform(.switchTo(other)))
        #expect(!gate.waitingForAlert)
        let dismissedAfterSwitch = gate.alertDismissed()
        #expect(!dismissedAfterSwitch)

        // Usual order: resolved first, then onChange after pendingLeave is cleared.
        let waiting = gate.next(after: .openFile, alertAlreadyGone: false)
        #expect(waiting == nil)
        #expect(gate.waitingForAlert)
        let shouldPresent = gate.alertDismissed()
        #expect(shouldPresent)
        // Only once: a later dismissal (a Cancel) does not open it again.
        #expect(!gate.waitingForAlert)
        let presentedAgain = gate.alertDismissed()
        #expect(!presentedAgain)

        // Early dismiss: onChange ran before resolved. next still presents once.
        var early = SongbookImporterGate()
        let earlyDismiss = early.alertDismissed()
        #expect(!earlyDismiss)
        let earlyNext = early.next(after: .openFile, alertAlreadyGone: true)
        #expect(earlyNext == .presentImporter)
        #expect(!early.waitingForAlert)
        let earlyAgain = early.alertDismissed()
        #expect(!earlyAgain)
    }

    /// Save keeps only what differs from the songbook; a draft equal to it in
    /// its own key drops the copy (SongPage commitEdit uses the same helper).
    @Test func commitKeepsOnlyWhatDiffersFromTheSongbook() {
        SongSessionEdits.reset()
        defer { SongSessionEdits.reset() }
        let chords = [SongChord.from(text: "C", characterNum: 0)]
        let source = SongSource(text: "Hello", chords: chords)
        let textOnly = SongSessionEdits.commit(id: 1, text: "Hi", chords: chords, steps: 0, source: source)
        #expect(textOnly == SongSessionEdits.Copy(text: "Hi", chords: nil, steps: 0))
        let keyOnly = SongSessionEdits.commit(id: 1, text: "Hello", chords: chords, steps: 2, source: source)
        #expect(keyOnly == SongSessionEdits.Copy(text: nil, chords: nil, steps: 2))
        let same = SongSessionEdits.commit(id: 1, text: "Hello", chords: chords, steps: 0, source: source)
        #expect(same == nil)
        #expect(SongSessionEdits.copy(for: 1) == nil)
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
