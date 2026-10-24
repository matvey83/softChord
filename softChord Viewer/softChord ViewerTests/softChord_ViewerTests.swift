//
//  softChord_ViewerTests.swift
//  softChord ViewerTests
//
//  Created by Matvey Adzhigirey on 10/21/26.
//

import SQLite3
import SwiftUI
import Testing
import UIKit
@testable import softChord_Viewer

struct softChord_ViewerTests {

    @Test func songMenuListsTheShareCommands() {
        let menu = SongShareMenu.menu(songId: { 1 }, report: { _, _ in }, onEdit: nil)
        let titles = menu.children.compactMap { ($0 as? UIAction)?.title }
        #expect(titles == [
            "Copy song text",
            "Copy song text with chords",
            "Copy as image",
            "Add to Photos",
        ])
    }

    @Test func songPageMenuAddsEdit() {
        let menu = SongShareMenu.menu(songId: { 1 }, report: { _, _ in }, onEdit: {})
        let titles = menu.children.compactMap { ($0 as? UIAction)?.title }
        #expect(titles.last == "Edit song text...")
    }

    /// The list must not refresh a menu while it is closed. The cell gets one
    /// interaction, and the items are built when that interaction asks for them.
    @Test @MainActor func songRowsInstallOneContextMenu() async {
        let controller = UIHostingController(rootView: ContentView(songs: [
            SongTitle(id: 1, title: "One"),
            SongTitle(id: 2, title: "Two"),
            SongTitle(id: 3, title: "Three"),
        ]))
        let window = show(controller)
        await settle()
        let cells = controller.view.descendants(of: UICollectionViewCell.self)
        #expect(cells.isEmpty == false)
        for cell in cells {
            let menus = cell.interactions.filter { $0 is UIContextMenuInteraction }
            #expect(menus.count == 1)
        }
        window.isHidden = true
    }

    /// The menu button sits at the top of the navigation bar, clear of the status bar.
    @Test @MainActor func songControlsSitAtTheTopOfTheBar() async throws {
        let song = try Songbook.titles().first
        let title = try #require(song)
        let controller = UIHostingController(rootView: NavigationStack {
            SongPage(song: title)
        })
        let window = show(controller)
        await settle()
        let menu = try #require(controller.view.window?.descendants(of: UIButton.self).first {
            $0.accessibilityLabel == "Menu"
        })
        let bar = try #require(controller.view.window?.descendants(of: UINavigationBar.self).first)
        let menuTop = menu.convert(menu.bounds, to: nil).minY
        let barTop = bar.convert(
            CGPoint(x: 0, y: bar.safeAreaLayoutGuide.layoutFrame.minY), to: nil).y
        let statusTop = window.safeAreaInsets.top
        #expect(menuTop + 1 >= statusTop)
        #expect(abs(menuTop - barTop) < 2)
        let down = try #require(window.descendants(of: UIButton.self).first {
            $0.accessibilityLabel == "Down"
        })
        let up = try #require(window.descendants(of: UIButton.self).first {
            $0.accessibilityLabel == "Up"
        })
        #expect(down.convert(down.bounds, to: nil).minY > menuTop)
        #expect(up.convert(up.bounds, to: nil).maxY < window.bounds.maxY)
        window.isHidden = true
    }

    /// A press anywhere on the menu or an arrow has to reach that button.
    /// The song is pushed, as it is from the list, so the bar container is in place.
    @Test @MainActor func songControlsTakeAPressAnywhereOnTheButton() async throws {
        let song = try Songbook.titles().first
        let title = try #require(song)
        let controller = UIHostingController(rootView: NavigationStack(path: .constant([title])) {
            Text("Songs")
                .toolbar(.hidden, for: .navigationBar)
                .navigationDestination(for: SongTitle.self) { song in
                    SongPage(song: song)
                }
        })
        let window = show(controller)
        await settle()
        window.layoutIfNeeded()
        try await checkSongControls(in: window)
        // The phone is used in landscape. The menu failed there.
        window.frame = CGRect(x: 0, y: 0, width: 852, height: 393)
        window.layoutIfNeeded()
        await settle()
        try await checkSongControls(in: window)
        window.isHidden = true
    }

    /// Back has to receive the press and return to the list. A press that only
    /// flashes the button leaves the song on screen.
    @Test @MainActor func backButtonReturnsToTheSongList() async throws {
        let song = try Songbook.titles().first
        let title = try #require(song)
        let controller = UIHostingController(rootView: SongListHarness(song: title))
        let window = show(controller)
        await settle()
        // Layout puts the bar container back in front. The buttons move above
        // it when the run loop is about to wait.
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            DispatchQueue.main.async {
                continuation.resume()
            }
        }
        let back = try #require(window.descendants(of: UIButton.self).first {
            $0.accessibilityLabel == "Back"
        })
        let area = back.convert(back.bounds, to: window).insetBy(dx: 1, dy: 1)
        #expect(area.width > 50)
        #expect(area.height > 16)
        let samples = [
            CGPoint(x: area.minX, y: area.minY),
            CGPoint(x: area.midX, y: area.minY),
            CGPoint(x: area.maxX, y: area.minY),
            CGPoint(x: area.minX, y: area.midY),
            CGPoint(x: area.midX, y: area.midY),
            CGPoint(x: area.maxX, y: area.midY),
            CGPoint(x: area.minX, y: area.maxY),
            CGPoint(x: area.midX, y: area.maxY),
            CGPoint(x: area.maxX, y: area.maxY),
        ]
        for point in samples {
            let hit = window.hitTest(point, with: nil)
            let onBack = hit === back || hit?.isDescendant(of: back) == true
            #expect(onBack, "\(point) hit \(hit.map { String(describing: type(of: $0)) } ?? "nil")")
        }
        let beside = CGPoint(x: area.maxX + 12, y: area.midY)
        let besideHit = window.hitTest(beside, with: nil)
        let besideIsBack = besideHit === back || besideHit?.isDescendant(of: back) == true
        #expect(besideIsBack == false)
        #expect(navigationController(in: window.rootViewController)?.viewControllers.count == 2)
        back.performPrimaryAction()
        // The pop starts immediately. The song buttons stay until the
        // transition takes the page off the window.
        var returned = false
        for _ in 0..<40 {
            await Task.yield()
            try await Task.sleep(for: .milliseconds(50))
            let backLeft = window.descendants(of: UIButton.self).contains {
                $0.accessibilityLabel == "Back"
            } == false
            let menuLeft = window.descendants(of: UIButton.self).contains {
                $0.accessibilityLabel == "Menu"
            } == false
            if backLeft && menuLeft {
                returned = true
                break
            }
        }
        #expect(returned)
        #expect(navigationController(in: window.rootViewController)?.viewControllers.count == 1)
        #expect(anyWindowShows("Songs"))
        window.isHidden = true
    }

    /// Save has to leave edit mode, and the field has to still be on screen
    /// when the keyboard starts hiding. Back from the editor returns to the list.
    @Test @MainActor func closingTheEditorWaitsForTheKeyboard() async throws {
        let song = try #require(Songbook.titles().first)
        let window = show(UIHostingController(rootView: SongListHarness(song: song)))
        await settle()
        try await openEditor(in: window)
        pressButton("Save", in: window)
        await waitUntil(in: window) { view in
            view.descendants(of: UITextView.self).isEmpty
        }
        #expect(window.descendants(of: UITextView.self).isEmpty)
        #expect(window.descendants(of: UIButton.self).contains { $0.accessibilityLabel == "Menu" })

        try await openEditor(in: window)
        let editor = try #require(window.descendants(of: UITextView.self).first)
        let stillUpAtHideStart = KeyboardHideNote()
        let willHide = NotificationCenter.default.addObserver(
            forName: UIResponder.keyboardWillHideNotification,
            object: nil,
            queue: .main
        ) { _ in
            stillUpAtHideStart.editorWasOnScreen = editor.window != nil
            stillUpAtHideStart.hideStarted = true
        }
        #expect(editor.becomeFirstResponder())
        await settle()
        pressButton("Save", in: window)
        await waitUntil(in: window) { view in
            view.descendants(of: UITextView.self).isEmpty
        }
        NotificationCenter.default.removeObserver(willHide)
        if stillUpAtHideStart.hideStarted {
            #expect(stillUpAtHideStart.editorWasOnScreen)
        }
        #expect(window.descendants(of: UITextView.self).isEmpty)
        window.isHidden = true

        let editBack = show(UIHostingController(rootView: SongListHarness(song: song)))
        await settle()
        try await openEditor(in: editBack)
        editBack.descendants(of: UITextView.self).first?.becomeFirstResponder()
        await settle()
        pressBack(in: editBack)
        // The Back button leaves with the chrome, before the page pops.
        await waitUntil(in: editBack) { view in
            navigationController(in: view.rootViewController)?.viewControllers.count == 1
        }
        #expect(navigationController(in: editBack.rootViewController)?.viewControllers.count == 1)
        #expect(editBack.descendants(of: UIButton.self).contains { $0.accessibilityLabel == "Back" } == false)
        editBack.isHidden = true

        // A tap outside the field resigns it before Back runs. The page has
        // to stay up until that hide finishes, then return to the list.
        let tappedAway = show(UIHostingController(rootView: SongListHarness(song: song)))
        await settle()
        try await openEditor(in: tappedAway)
        let typing = try #require(tappedAway.descendants(of: UITextView.self).first)
        #expect(typing.becomeFirstResponder())
        await settle()
        #expect(typing.resignFirstResponder())
        pressBack(in: tappedAway)
        #expect(navigationController(in: tappedAway.rootViewController)?.viewControllers.count == 2)
        await waitUntil(in: tappedAway) { view in
            navigationController(in: view.rootViewController)?.viewControllers.count == 1
        }
        #expect(navigationController(in: tappedAway.rootViewController)?.viewControllers.count == 1)
        tappedAway.isHidden = true
    }

    @MainActor private func openEditor(in window: UIWindow) async throws {
        try performMenuAction("Edit song text...", in: window)
        await waitUntil(in: window) { view in
            view.descendants(of: UITextView.self).isEmpty == false
        }
        #expect(window.descendants(of: UITextView.self).isEmpty == false)
    }

    @MainActor private func pressBack(in window: UIWindow) {
        window.descendants(of: UIButton.self).first { $0.accessibilityLabel == "Back" }?.performPrimaryAction()
    }

    @MainActor private func pressButton(_ title: String, in window: UIWindow) {
        let button = window.descendants(of: UIButton.self).first {
            $0.accessibilityLabel == title || $0.configuration?.title == title
        }
        button?.sendActions(for: .touchUpInside)
    }

    @MainActor private func performMenuAction(_ title: String, in window: UIWindow) throws {
        let menu = try #require(window.descendants(of: UIButton.self).first { $0.accessibilityLabel == "Menu" })
        let action = try #require(menu.menu?.children.compactMap { $0 as? UIAction }.first { $0.title == title })
        action.performWithSender(menu, target: nil)
    }

    @MainActor private func waitUntil(in window: UIWindow, _ done: (UIWindow) -> Bool) async {
        for _ in 0..<40 {
            if done(window) {
                return
            }
            await Task.yield()
            try? await Task.sleep(for: .milliseconds(50))
        }
    }

    @MainActor private func navigationController(in controller: UIViewController?) -> UINavigationController? {
        guard let controller else {
            return nil
        }
        if let navigation = controller as? UINavigationController {
            return navigation
        }
        for child in controller.children {
            if let found = navigationController(in: child) {
                return found
            }
        }
        return nil
    }

    /// Whole button, in front of the bar container, and the menu actually opens.
    @MainActor private func checkSongControls(in window: UIWindow) async throws {
        // Layout puts the bar container back in front. The buttons move above
        // it when the run loop is about to wait.
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            DispatchQueue.main.async {
                continuation.resume()
            }
        }
        for name in ["Menu", "Down", "Up"] {
            let button = try #require(window.descendants(of: UIButton.self).first {
                $0.accessibilityLabel == name
            })
            var reachedWindow = false
            var ancestor: UIView? = button
            while let view = ancestor {
                if view.superview === window {
                    reachedWindow = true
                }
                ancestor = view.superview
            }
            #expect(reachedWindow)
            let area = button.convert(button.bounds, to: window).insetBy(dx: 1, dy: 1)
            #expect(area.width > 20)
            #expect(area.height > 20)
            let samples = [
                CGPoint(x: area.minX, y: area.minY),
                CGPoint(x: area.midX, y: area.minY),
                CGPoint(x: area.maxX, y: area.minY),
                CGPoint(x: area.minX, y: area.midY),
                CGPoint(x: area.midX, y: area.midY),
                CGPoint(x: area.maxX, y: area.midY),
                CGPoint(x: area.minX, y: area.maxY),
                CGPoint(x: area.midX, y: area.maxY),
                CGPoint(x: area.maxX, y: area.maxY),
            ]
            for point in samples {
                #expect(window.hitTest(point, with: nil) === button)
            }
        }
        let menu = try #require(window.descendants(of: UIButton.self).first {
            $0.accessibilityLabel == "Menu"
        })
        #expect(menu.showsMenuAsPrimaryAction)
        #expect(menu.menu?.children.isEmpty == false)
        let presenter = menuPresenter(of: menu)
        #expect(presenter?.view.window === window)
        #expect(menu.isDescendant(of: presenter?.view ?? UIView()))
        #expect(controllerIsInTheWindowHierarchy(presenter))
        if let chrome = chromePanel(containing: menu, in: presenter?.view) {
            let middle = CGPoint(x: window.bounds.midX, y: window.bounds.midY)
            let middleHit = window.hitTest(middle, with: nil)
            let hitsChrome = middleHit === chrome || middleHit?.isDescendant(of: chrome) == true
            #expect(hitsChrome == false)
        }
        controlsAreInFrontOfTheBar(menu, window: window)
        menu.performPrimaryAction()
        await settle()
        #expect(menu.isHeld)
        #expect(anyWindowShows("Copy song text"))
        menu.contextMenuInteraction?.dismissMenu()
    }

    /// The buttons have to be in front of the bar container. That container
    /// takes presses that land on whatever is behind it.
    @MainActor private func controlsAreInFrontOfTheBar(_ menu: UIView, window: UIWindow) {
        let bars = window.descendants(of: UIView.self).filter {
            String(describing: type(of: $0)).contains("FloatingBar")
        }
        if bars.isEmpty {
            Issue.record("Floating bar is missing")
            return
        }
        for bar in bars {
            guard let parent = commonParent(menu, bar),
                  let menuIndex = childIndex(of: menu, in: parent),
                  let barIndex = childIndex(of: bar, in: parent) else {
                Issue.record("Could not place the menu and the bar")
                return
            }
            if menuIndex <= barIndex {
                let names = parent.subviews.map { String(describing: type(of: $0)) }
                Issue.record("Song buttons are not in front of the bar. Siblings: \(names)")
            }
        }
    }

    @MainActor private func commonParent(_ first: UIView, _ second: UIView) -> UIView? {
        var seen: [ObjectIdentifier: UIView] = [:]
        var current: UIView? = first
        while let view = current {
            seen[ObjectIdentifier(view)] = view
            current = view.superview
        }
        current = second
        while let view = current {
            if let parent = seen[ObjectIdentifier(view)] {
                return parent
            }
            current = view.superview
        }
        return nil
    }

    /// The button panel added to the controller that presents the menu.
    @MainActor private func chromePanel(containing menu: UIView, in root: UIView?) -> UIView? {
        var current: UIView? = menu
        while let view = current {
            if view.superview === root {
                return view
            }
            current = view.superview
        }
        return nil
    }

    @MainActor private func childIndex(of view: UIView, in parent: UIView) -> Int? {
        var current: UIView? = view
        while let node = current {
            if node.superview === parent {
                return parent.subviews.firstIndex(of: node)
            }
            current = node.superview
        }
        return nil
    }

    /// A detached controller can open a menu once, then the gesture gate times out.
    @MainActor private func controllerIsInTheWindowHierarchy(_ controller: UIViewController?) -> Bool {
        guard let controller, controller.view.window != nil else {
            return false
        }
        var top = controller
        while let parent = top.parent {
            top = parent
        }
        return top === controller.view.window?.rootViewController
    }

    /// The controller that owns an ancestor view. The window does not count.
    @MainActor private func menuPresenter(of view: UIView) -> UIViewController? {
        var current: UIView? = view
        while let ancestor = current, !(ancestor is UIWindow) {
            if let controller = ancestor.next as? UIViewController, controller.view === ancestor {
                return controller
            }
            current = ancestor.superview
        }
        return nil
    }

    @MainActor private func anyWindowShows(_ text: String) -> Bool {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        for scene in scenes {
            for window in scene.windows where windowShows(text, in: window) {
                return true
            }
        }
        return false
    }

    @MainActor private func windowShows(_ text: String, in view: UIView) -> Bool {
        if view.accessibilityLabel == text {
            return true
        }
        if let label = view as? UILabel, label.text == text {
            return true
        }
        return view.subviews.contains { windowShows(text, in: $0) }
    }


    @Test func songTextMatchesTheEditorLayout() {
        let chords = [
            SongChord(characterNum: 0, noteId: 0, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false),
            SongChord(characterNum: 5, noteId: 9, chordTypeId: 1, bassNoteId: -1, marker: "", inParentheses: false),
            SongChord(characterNum: 26, noteId: 7, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false),
        ]
        let text = "Test line one\nTest line two"
        let withChords = SongText.render(text: text, chords: chords, includeChords: true)
        #expect(withChords == "C    Am\r\nTest line one\r\n" + String(repeating: " ", count: 11) + "G\r\nTest line two")

        let plain = SongText.render(text: text, chords: chords, includeChords: false)
        #expect(plain == "Test line one\r\nTest line two")
    }

    @Test func sheetAnchorsChordsOnTheirLetters() {
        let chords = [
            SongChord(characterNum: 0, noteId: 0, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false),
            SongChord(characterNum: 5, noteId: 9, chordTypeId: 1, bassNoteId: -1, marker: "", inParentheses: false),
            SongChord(characterNum: 26, noteId: 7, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false),
        ]
        let lines = SongText.sheet(text: "Test line one\nTest line two", chords: chords)
        #expect(lines.map(\.lyric) == ["Test line one", "Test line two"])
        #expect(lines[0].chords == [
            SongSheetChord(anchor: 0, text: "C"),
            SongSheetChord(anchor: 5, text: "Am"),
        ])
        #expect(lines[1].chords == [SongSheetChord(anchor: 12, text: "G")])
    }

    @Test func chordTextKeepsMarkerBassAndParentheses() {
        let chord = SongChord(
            characterNum: 0, noteId: 0, chordTypeId: 0, bassNoteId: 4, marker: "1", inParentheses: true)
        let rendered = SongText.render(text: "Hello world", chords: [chord], includeChords: true)
        #expect(rendered == "(1:C/E)\r\nHello world")
    }

    @Test func editingLyricsKeepsAChordOnItsLetter() {
        let chord = SongChord(
            characterNum: 4, noteId: 0, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false)
        let inserted = SongLyricChords.moved([chord], from: "Hello", to: "HeXllo")
        #expect(inserted.map(\.characterNum) == [5])

        let onTheFirstLetter = SongChord(
            characterNum: 0, noteId: 7, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false)
        let deleted = SongLyricChords.moved([onTheFirstLetter, chord], from: "Hello", to: "ello")
        #expect(deleted.map(\.characterNum) == [3])
    }

    @Test func aPressInsideAChordBoxPicksThatLetter() {
        let boxes = [
            SongChordBoxes.Box(characterNum: 0, rect: CGRect(x: 10, y: 8, width: 20, height: 12)),
            SongChordBoxes.Box(characterNum: 4, rect: CGRect(x: 40, y: 8, width: 24, height: 12)),
        ]
        #expect(SongChordBoxes.characterNum(at: CGPoint(x: 50, y: 14), boxes: boxes) == 4)
        // The border is the letter's, so a tap there can still edit the text.
        #expect(SongChordBoxes.characterNum(at: CGPoint(x: 10, y: 14), boxes: boxes) == nil)
        #expect(SongChordBoxes.characterNum(at: CGPoint(x: 30, y: 14), boxes: boxes) == nil)
    }

    /// The edit-mode chord layer is laid out in the text view's coordinates.
    /// Those stay put when the song scrolls, so the chords can scroll with the letters.
    @Test @MainActor func caretRectStaysWithTheDocumentWhileScrolling() {
        let frame = CGRect(x: 0, y: 0, width: 220, height: 140)
        let view = UITextView(frame: frame)
        view.font = UIFont(name: "TimesNewRomanPSMT", size: 20)
        view.textContainerInset = UIEdgeInsets(top: 16, left: 16, bottom: 16, right: 16)
        view.text = String(repeating: "Line of lyric text here\n", count: 40)
        let window = UIWindow(windowScene: windowScene())
        window.frame = frame
        window.addSubview(view)
        window.makeKeyAndVisible()
        view.layoutIfNeeded()
        let before = view.caretRect(for: view.beginningOfDocument)
        #expect(before.isNull == false)
        view.setContentOffset(CGPoint(x: 0, y: 100), animated: false)
        view.layoutIfNeeded()
        #expect(view.contentOffset.y > 40)
        let after = view.caretRect(for: view.beginningOfDocument)
        #expect(abs(before.minY - after.minY) < 1)
    }

    /// A chord overlay sized to the song must not stretch the song.
    @Test @MainActor func textViewContentSizeIgnoresAnOverlay() {
        let frame = CGRect(x: 0, y: 0, width: 220, height: 140)
        let view = UITextView(frame: frame)
        view.font = UIFont(name: "TimesNewRomanPSMT", size: 20)
        view.text = "Hello\nWorld\n"
        let window = UIWindow(windowScene: windowScene())
        window.frame = frame
        window.addSubview(view)
        window.makeKeyAndVisible()
        view.layoutIfNeeded()
        let before = view.contentSize
        #expect(before.height > 20)
        let overlay = UIView(frame: CGRect(origin: .zero, size: before))
        overlay.isUserInteractionEnabled = false
        view.addSubview(overlay)
        view.layoutIfNeeded()
        #expect(abs(view.contentSize.height - before.height) < 1)
        #expect(abs(view.contentSize.width - before.width) < 1)
    }

    @MainActor private func windowScene() -> UIWindowScene {
        let scene = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first
        precondition(scene != nil)
        return scene!
    }

    @MainActor private func show(_ controller: UIViewController) -> UIWindow {
        let window = UIWindow(windowScene: windowScene())
        window.frame = CGRect(x: 0, y: 0, width: 402, height: 874)
        window.rootViewController = controller
        window.makeKeyAndVisible()
        controller.view.layoutIfNeeded()
        return window
    }

    @MainActor private func settle() async {
        for _ in 0..<8 {
            await Task.yield()
            await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
                    continuation.resume()
                }
            }
        }
    }

    @Test func blankLinesStayInTheSheet() {
        let lines = SongText.sheet(text: "One\n\nTwo", chords: [])
        #expect(lines.map(\.lyric) == ["One", "", "Two"])
    }

    @Test func aMajorSpellsSharps() {
        let chords = progression([(9, 0), (4, 0), (6, 1), (2, 0)], times: 3)
        let rendered = SongText.render(text: String(repeating: "x", count: 80), chords: chords, includeChords: true)
        #expect(rendered.contains("F♯"))
        #expect(!rendered.contains("G♭"))
    }

    @Test func bFlatMajorSpellsFlats() {
        let chords = progression([(10, 0), (5, 0), (7, 1), (3, 0)], times: 3)
        let rendered = SongText.render(text: String(repeating: "x", count: 80), chords: chords, includeChords: true)
        #expect(rendered.contains("B♭"))
        #expect(rendered.contains("E♭"))
        #expect(!rendered.contains("A♯"))
    }

    @Test func cMajorSpellsCSharpAndEFlat() {
        var chords = progression([(0, 0), (7, 0), (9, 1)], times: 4)
        chords.append(chord(at: 80, note: 1))
        chords.append(chord(at: 84, note: 3))
        let rendered = SongText.render(text: String(repeating: "x", count: 100), chords: chords, includeChords: true)
        #expect(rendered.contains("C♯"))
        #expect(rendered.contains("E♭"))
        #expect(!rendered.contains("D♭"))
        #expect(!rendered.contains("D♯"))
    }

    @Test func modulationKeepsEachRegionsSpelling() {
        let aMajor = progression([(9, 0), (4, 0), (6, 1), (2, 0)], times: 4)
        let bFlat = progression([(10, 0), (5, 0), (7, 1), (3, 0)], times: 4, start: 200)
        let rendered = SongText.render(
            text: String(repeating: "x", count: 400), chords: aMajor + bFlat, includeChords: true)
        #expect(rendered.contains("F♯"))
        #expect(rendered.contains("B♭"))
        #expect(!rendered.contains("G♭"))
    }

}

struct SongTransposeTests {
    @Test func halfStepUpMovesRootAndBass() {
        let chord = SongChord(
            characterNum: 4, noteId: 0, chordTypeId: 1, bassNoteId: 7, marker: "2", inParentheses: true)
        let up = SongTranspose.shifted([chord], by: 1)
        #expect(up == [
            SongChord(
                characterNum: 4, noteId: 1, chordTypeId: 1, bassNoteId: 8, marker: "2", inParentheses: true),
        ])
    }

    @Test func halfStepDownWrapsCToBAndLeavesAMissingBass() {
        let chord = SongChord(
            characterNum: 0, noteId: 0, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false)
        let down = SongTranspose.shifted([chord], by: -1)
        #expect(down[0].noteId == 11)
        #expect(down[0].bassNoteId == -1)
    }

    @Test func anOctaveOfHalfStepsIsTheOriginalChord() {
        let chord = SongChord(
            characterNum: 2, noteId: 5, chordTypeId: 4, bassNoteId: 9, marker: "", inParentheses: false)
        #expect(SongTranspose.shifted([chord], by: 12) == [chord])
        #expect(SongTranspose.shifted([chord], by: -12) == [chord])
        #expect(SongTranspose.shifted([chord], by: 0) == [chord])
    }

    @Test func transposedChordsSpellTheNewKey() {
        let chords = progression([(9, 0), (4, 0), (6, 1), (2, 0)], times: 3)
        let rendered = SongText.render(
            text: String(repeating: "x", count: 80),
            chords: SongTranspose.shifted(chords, by: 1),
            includeChords: true)
        #expect(rendered.contains("B♭"))
        #expect(rendered.contains("E♭"))
        #expect(!rendered.contains("A♯"))
    }
}

struct SongFilterTests {
    @Test func blankFilterKeepsEverySong() {
        let songs = sampleSongs
        #expect(SongFilter.matching("   ", in: songs) == songs)
    }

    @Test func filterMatchesInsideTheTitleIgnoringCase() {
        let songs = sampleSongs
        #expect(SongFilter.matching("alp", in: songs).map(\.id) == [1, 3])
        #expect(SongFilter.matching("БОГ", in: songs).map(\.id) == [4])
        #expect(SongFilter.matching("мы с", in: songs).map(\.id) == [5])
        #expect(SongFilter.matching("zzz", in: songs).isEmpty)
    }

    private var sampleSongs: [SongTitle] {
        [
            SongTitle(id: 1, title: "Alpha"),
            SongTitle(id: 2, title: "beta Song"),
            SongTitle(id: 3, title: "Alpine"),
            SongTitle(id: 4, title: "Бог моя защита"),
            SongTitle(id: 5, title: "Вместе мы с вами"),
        ]
    }
}

private final class KeyboardHideNote: @unchecked Sendable {
    var hideStarted = false
    var editorWasOnScreen = false
}

/// Opens one song the way the list does, with a path Back can clear.
private struct SongListHarness: View {
    @State private var path: [SongTitle]

    init(song: SongTitle) {
        _path = State(initialValue: [song])
    }

    var body: some View {
        NavigationStack(path: $path) {
            SongListTitle()
                .toolbar(.hidden, for: .navigationBar)
                .navigationDestination(for: SongTitle.self) { song in
                    SongPage(song: song)
                }
        }
    }
}

/// A real label, so the test can see that the list came back.
private struct SongListTitle: UIViewRepresentable {
    func makeUIView(context: Context) -> UILabel {
        let label = UILabel()
        label.text = "Songs"
        return label
    }

    func updateUIView(_ label: UILabel, context: Context) {}
}

private extension UIView {
    func descendants<T: UIView>(of type: T.Type) -> [T] {
        var found: [T] = []
        for child in subviews {
            if let match = child as? T {
                found.append(match)
            }
            found.append(contentsOf: child.descendants(of: type))
        }
        return found
    }
}

struct SongSheetLayoutTests {
    @Test func chordSitsAboveItsLyric() {
        let drawing = SongSheetLayout.drawing(for: [
            SongSheetLine(lyric: "Hello", chords: [SongSheetChord(anchor: 0, text: "C")]),
        ])
        let lyric = drawing.glyphs.first { $0.text == "Hello" }
        let chord = drawing.glyphs.first { $0.text == "C" }
        #expect(lyric != nil)
        #expect(chord != nil)
        #expect(chord!.baseline < lyric!.baseline)
        #expect(lyric!.x == 16)
        #expect(colorParts(lyric!.color) == [0, 1])
        #expect(colorParts(chord!.color) == [0, 0, 1, 1])
        #expect(drawing.glyphs.allSatisfy { $0.x >= 0 })
    }

    @Test func chordsAddHeightAndLongerLyricsAddWidth() {
        let plain = SongSheetLayout.drawing(for: [SongSheetLine(lyric: "Hello", chords: [])])
        let withChord = SongSheetLayout.drawing(for: [
            SongSheetLine(lyric: "Hello", chords: [SongSheetChord(anchor: 0, text: "C")]),
        ])
        let longer = SongSheetLayout.drawing(for: [SongSheetLine(lyric: "Hello there", chords: [])])
        #expect(withChord.size.height > plain.size.height)
        #expect(longer.size.width > plain.size.width)
    }
}

@MainActor
struct SongSheetImageTests {
    @Test func imageIsWhiteWithBlackLyricsAndBlueChords() {
        let lines = [SongSheetLine(lyric: "Hello", chords: [SongSheetChord(anchor: 0, text: "C")])]
        let drawing = SongSheetLayout.drawing(for: lines)
        let image = SongSheetImage.image(for: lines, scale: 1)
        // The renderer rounds the sheet up to a whole point, which adds a sliver of white.
        #expect(image.size.width >= drawing.size.width && image.size.width < drawing.size.width + 1)
        #expect(image.size.height >= drawing.size.height && image.size.height < drawing.size.height + 1)
        #expect(image.scale == 1)
        let pixels = pixels(of: image)
        #expect(pixels.contains { $0.x > 250 && $0.y > 250 && $0.z > 250 })
        #expect(pixels.contains { $0.x < 40 && $0.y < 40 && $0.z < 40 })
        #expect(pixels.contains { $0.x < 80 && $0.y < 80 && $0.z > 180 })
    }
}

struct SongbookReadTests {
    @Test func readsTitlesTextAndChordsFromASongbook() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("songbook-\(UUID().uuidString).songbook")
        defer { try? FileManager.default.removeItem(at: url) }
        try writeSongbook(at: url)

        let titles = try Songbook.titles(in: url)
        #expect(titles.map(\.id) == [1, 2])
        #expect(titles.map(\.title) == ["Alpha", "beta Song"])

        let plain = try Songbook.songText(id: 1, includeChords: false, in: url)
        #expect(plain == "Hello")
        let withChord = try Songbook.songText(id: 1, includeChords: true, in: url)
        #expect(withChord == "C\r\nHello")

        let marked = try Songbook.songText(id: 2, includeChords: true, in: url)
        #expect(marked == "(1:C/E)\r\nHello world")

        let sheet = try Songbook.sheet(id: 1, in: url)
        let source = try Songbook.source(id: 2, in: url)
        #expect(source.text == "Hello world")
        #expect(source.chords == [
            SongChord(
                characterNum: 0, noteId: 0, chordTypeId: 0, bassNoteId: 4, marker: "1", inParentheses: true),
        ])

        #expect(sheet == [SongSheetLine(lyric: "Hello", chords: [SongSheetChord(anchor: 0, text: "C")])])

        #expect(throws: SongbookError.songNotFound) {
            try Songbook.sheet(id: 99, in: url)
        }
    }
}

private func chord(at character: Int, note: Int, type: Int = 0) -> SongChord {
    SongChord(
        characterNum: character, noteId: note, chordTypeId: type, bassNoteId: -1, marker: "", inParentheses: false)
}

private func progression(_ pairs: [(Int, Int)], times: Int, start: Int = 0, step: Int = 4) -> [SongChord] {
    var chords: [SongChord] = []
    var character = start
    for _ in 0..<times {
        for (note, type) in pairs {
            chords.append(chord(at: character, note: note, type: type))
            character += step
        }
    }
    return chords
}

private func colorParts(_ color: CGColor) -> [CGFloat] {
    color.components ?? []
}

private func pixels(of image: UIImage) -> [SIMD3<UInt8>] {
    guard let cgImage = image.cgImage else {
        return []
    }
    let width = cgImage.width
    let height = cgImage.height
    var bytes = [UInt8](repeating: 0, count: width * height * 4)
    bytes.withUnsafeMutableBytes { buffer in
        guard let context = CGContext(
            data: buffer.baseAddress,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: width * 4,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else {
            return
        }
        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))
    }
    var colors: [SIMD3<UInt8>] = []
    colors.reserveCapacity(width * height)
    var index = 0
    while index + 3 < bytes.count {
        colors.append(SIMD3(bytes[index], bytes[index + 1], bytes[index + 2]))
        index += 4
    }
    return colors
}

private func songbookSchema() throws -> String {
    let url = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("src/songbook.sql")
    return try String(contentsOf: url, encoding: .utf8)
}

private func writeSongbook(at url: URL) throws {
    var db: OpaquePointer?
    if sqlite3_open(url.path, &db) != SQLITE_OK {
        throw SongbookError.openFailed("Could not create the test songbook.")
    }
    guard let db else {
        throw SongbookError.openFailed("Could not create the test songbook.")
    }
    defer { sqlite3_close(db) }
    try exec(db, try songbookSchema())
    try exec(
        db,
        """
        INSERT INTO songs (id, text, title) VALUES (2, 'Hello world', 'beta Song');
        INSERT INTO songs (id, text, title) VALUES (1, 'Hello', 'Alpha');
        INSERT INTO song_chord_link (
            song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses)
        VALUES (1, 0, 0, 0, NULL, '-1', 0);
        INSERT INTO song_chord_link (
            song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses)
        VALUES (2, 0, 0, 0, 4, '1', 1);
        """)
}

private func exec(_ db: OpaquePointer, _ sql: String) throws {
    var error: UnsafeMutablePointer<CChar>?
    if sqlite3_exec(db, sql, nil, nil, &error) != SQLITE_OK {
        let message = error.map { String(cString: $0) } ?? "Could not write the test songbook."
        sqlite3_free(error)
        throw SongbookError.queryFailed(message)
    }
}
