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

    @Test func songPageMenuAddsEditChordsNextToEditText() {
        let menu = SongShareMenu.menu(songId: { 1 }, report: { _, _ in }, onEdit: {}, onEditChords: {})
        let titles = menu.children.compactMap { ($0 as? UIAction)?.title }
        #expect(Array(titles.suffix(2)) == ["Edit song text...", "Edit song chords..."])
        let listMenu = SongShareMenu.menu(songId: { 1 }, report: { _, _ in }, onEdit: nil)
        let listTitles = listMenu.children.compactMap { ($0 as? UIAction)?.title }
        #expect(!listTitles.contains("Edit song chords..."))
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

    /// Reset transpose sits with Down and Up. It is dimmed until the song has been
    /// moved, brings the song back to the key it had when it was opened, and is
    /// dimmed again when Up and Down cancel out.
    @Test @MainActor func resetTransposeIsDimmedUntilTheSongIsMoved() async throws {
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
        func reset() throws -> UIButton {
            try #require(window.descendants(of: UIButton.self).first {
                $0.accessibilityLabel == "Reset transpose"
            })
        }
        let down = try #require(window.descendants(of: UIButton.self).first { $0.accessibilityLabel == "Down" })
        let resetButton = try reset()
        // Same row as Down and Up, after them.
        let up = try #require(window.descendants(of: UIButton.self).first { $0.accessibilityLabel == "Up" })
        let upFrame = up.convert(up.bounds, to: nil)
        let resetFrame = resetButton.convert(resetButton.bounds, to: nil)
        #expect(abs(upFrame.midY - resetFrame.midY) < 1)
        #expect(resetFrame.minX >= upFrame.maxX)
        #expect(down.convert(down.bounds, to: nil).maxX <= upFrame.minX)
        // Untouched song: dimmed.
        #expect(try reset().isEnabled == false)
        // Moved: on.
        pressButton("Up", in: window)
        await settle()
        #expect(try reset().isEnabled)
        // A press anywhere on the live button reaches it.
        let live = try reset().convert(try reset().bounds, to: window).insetBy(dx: 1, dy: 1)
        for point in [CGPoint(x: live.minX, y: live.minY), CGPoint(x: live.midX, y: live.midY),
                      CGPoint(x: live.maxX, y: live.maxY)] {
            #expect(window.hitTest(point, with: nil) === (try reset()))
        }
        // Up then Down by the same amount is the opened key again: dimmed.
        pressButton("Down", in: window)
        await settle()
        #expect(try reset().isEnabled == false)
        // Several steps, then Reset goes straight back, and a second press does nothing.
        pressButton("Down", in: window)
        pressButton("Down", in: window)
        pressButton("Down", in: window)
        await settle()
        #expect(try reset().isEnabled)
        pressButton("Reset transpose", in: window)
        await settle()
        #expect(try reset().isEnabled == false)
        // A whole octave shows the same chords, so that is the loaded key too.
        for _ in 0..<12 { pressButton("Up", in: window) }
        await settle()
        #expect(try reset().isEnabled == false)
        window.isHidden = true
    }

    /// Edit chord and Delete chord sit under Discard and Save, one row each, on one
    /// line, and the chord view starts below them.
    @Test @MainActor func chordButtonsSitBelowSaveAndTheTextStartsBelowThem() async throws {
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
        let menu = try #require(window.descendants(of: UIButton.self).first { $0.accessibilityLabel == "Menu" })
        let action = try #require(menu.menu?.children.compactMap { $0 as? UIAction }.first {
            $0.title == "Edit song chords..."
        })
        action.performWithSender(nil, target: nil)
        await settle()
        let sizes: [(CGSize, UIContentSizeCategory)] = [
            (CGSize(width: 402, height: 874), .large),
            (CGSize(width: 852, height: 393), .large),
            (CGSize(width: 402, height: 874), .accessibilityLarge),
        ]
        for (size, category) in sizes {
            window.frame = CGRect(origin: .zero, size: size)
            controller.traitOverrides.preferredContentSizeCategory = category
            window.layoutIfNeeded()
            await settle()
            func button(_ name: String) throws -> UIButton {
                try #require(window.descendants(of: UIButton.self).first {
                    $0.configuration?.title == name && !$0.isHidden
                })
            }
            let save = try button("Save").convert(try button("Save").bounds, to: window)
            let edit = try button("Edit chord")
            let delete = try button("Delete chord")
            let editFrame = edit.convert(edit.bounds, to: window)
            let deleteFrame = delete.convert(delete.bounds, to: window)
            #expect(editFrame.minY >= save.maxY, "\(size) \(category)")
            #expect(deleteFrame.minY >= editFrame.maxY, "\(size) \(category)")
            // One line of the button's own font, plus its padding.
            let font = UIFont.preferredFont(forTextStyle: .footnote, compatibleWith: delete.traitCollection)
            #expect(deleteFrame.height < font.lineHeight * 2 + 8, "\(size) \(category) \(deleteFrame)")
            let chords = try #require(window.descendants(of: UIView.self).first {
                $0.accessibilityIdentifier == "Song chords"
            })
            let chordsFrame = chords.convert(chords.bounds, to: window)
            #expect(chordsFrame.minY >= deleteFrame.maxY, "\(size) \(category) \(chordsFrame)")
        }
        // The chord view zooms and scrolls like the song view.
        let sheet = try #require(window.descendants(of: UIScrollView.self).first {
            $0.accessibilityIdentifier == "Song chords"
        })
        #expect(sheet.gestureRecognizers?.contains { $0 is UIPinchGestureRecognizer } == true)
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
        // The hide can already be over when resign returns: the simulator
        // may show no software keyboard, or finish the hide at once. Only a
        // hide that is still running has to hold the page.
        let tapHide = KeyboardHideNote()
        let center = NotificationCenter.default
        let tapWillHide = center.addObserver(
            forName: UIResponder.keyboardWillHideNotification,
            object: nil,
            queue: .main
        ) { _ in
            tapHide.hideStarted = true
        }
        let tapDidHide = center.addObserver(
            forName: UIResponder.keyboardDidHideNotification,
            object: nil,
            queue: .main
        ) { _ in
            tapHide.hideFinished = true
        }
        #expect(typing.resignFirstResponder())
        let hideStillRunning = tapHide.hideStarted && !tapHide.hideFinished
        pressBack(in: tappedAway)
        if hideStillRunning {
            #expect(navigationController(in: tappedAway.rootViewController)?.viewControllers.count == 2)
        }
        await waitUntil(in: tappedAway) { view in
            navigationController(in: view.rootViewController)?.viewControllers.count == 1
        }
        #expect(navigationController(in: tappedAway.rootViewController)?.viewControllers.count == 1)
        center.removeObserver(tapWillHide)
        center.removeObserver(tapDidHide)
        tappedAway.isHidden = true
    }

    /// Save keeps the letters for this run. Opening the song again shows them.
    /// Saving the songbook text again drops that copy. The file is not written.
    @Test @MainActor func savedSongTextStaysForThisRun() async throws {
        SongSessionEdits.reset()
        defer { SongSessionEdits.reset() }
        let song = try #require(Songbook.titles().first)
        let first = show(UIHostingController(rootView: NavigationStack {
            SongPage(song: song)
        }))
        await settle()
        try await openEditor(in: first)
        let editor = try #require(first.descendants(of: UITextView.self).first)
        let original = editor.text ?? ""
        let marked = original + "§keep"
        editor.text = marked
        editor.delegate?.textViewDidChange?(editor)
        pressButton("Save", in: first)
        await waitUntil(in: first) { view in
            view.descendants(of: UITextView.self).isEmpty
        }
        #expect(SongSessionEdits.copy(for: song.id)?.text == marked)
        first.isHidden = true

        let second = show(UIHostingController(rootView: NavigationStack {
            SongPage(song: song)
        }))
        await settle()
        try await openEditor(in: second)
        let again = try #require(second.descendants(of: UITextView.self).first)
        #expect(again.text == marked)

        again.text = original
        again.delegate?.textViewDidChange?(again)
        pressButton("Save", in: second)
        await waitUntil(in: second) { view in
            view.descendants(of: UITextView.self).isEmpty
        }
        #expect(SongSessionEdits.copy(for: song.id) == nil)
        second.isHidden = true

        let third = show(UIHostingController(rootView: NavigationStack {
            SongPage(song: song)
        }))
        await settle()
        try await openEditor(in: third)
        let restored = try #require(third.descendants(of: UITextView.self).first)
        #expect(restored.text == original)
        third.isHidden = true
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
        for name in ["Menu", "Down", "Up", "Reset transpose"] {
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
            // A dimmed button (Reset transpose before the song is moved) takes no
            // press, so only a live button is hit tested.
            for point in samples where button.isEnabled {
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

    @Test func draggingAChordAttachesItToAnotherLetter() {
        let chord = SongChord(
            characterNum: 0, noteId: 0, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false)
        let other = SongChord(
            characterNum: 4, noteId: 7, chordTypeId: 1, bassNoteId: -1, marker: "", inParentheses: false)
        let moved = SongLyricChords.reattached([chord, other], from: 0, to: 2)
        #expect(moved.map(\.characterNum) == [2, 4])
        // A letter never gets two chords, and no chord is dropped.
        let occupied = SongLyricChords.reattached([chord, other], from: 0, to: 4)
        #expect(occupied == [chord, other])
        #expect(SongLyricChords.reattached([chord], from: 0, to: 0).map(\.characterNum) == [0])
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

    @Test func aPressBesideAChordPicksThatLetter() {
        let boxes = [
            SongChordBoxes.Box(characterNum: 4, rect: CGRect(x: 40, y: 8, width: 24, height: 12)),
        ]
        let beside = CGPoint(x: 36, y: 14)
        #expect(SongChordBoxes.characterNum(at: beside, boxes: boxes, slop: SongChordPick.slop) == 4)
        #expect(SongChordBoxes.characterNum(at: beside, boxes: boxes) == nil)
    }

    @Test func aTapOnTheSelectedLetterEditsItsChord() {
        // A letter with no chord, pressed again, is a new chord.
        #expect(SongChordPick.action(
            selected: 2, hit: 2, pressedSelectedChord: false, selectedHasChord: false) == .edit)
        // The selected chord's letter, pressed below the chord, edits it as well.
        #expect(SongChordPick.action(
            selected: 4, hit: 4, pressedSelectedChord: false, selectedHasChord: true) == .edit)
        // The chord itself still drags first. A tap in place edits it.
        #expect(SongChordPick.action(
            selected: 4, hit: 4, pressedSelectedChord: true, selectedHasChord: true) == .drag)
    }

    @Test func aTypedChordReplacesOrAddsTheChordOnThatLetter() {
        let c = SongChord.from(text: "C", characterNum: 0)
        let g = SongChord.from(text: "G", characterNum: 6)
        let replaced = SongLyricChords.replaced([c, g], at: 0, withText: "Am7/G", steps: 0)
        #expect(replaced.map(\.characterNum) == [0, 6])
        #expect(SoftchordChords.chordText(replaced[0], prefer: 2) == "Am7/G")
        #expect(replaced[1] == g)
        let added = SongLyricChords.replaced([c, g], at: 3, withText: "F", steps: 0)
        #expect(added.map(\.characterNum) == [0, 3, 6])
        #expect(SongLyricChords.deleted(added, at: 3) == [c, g])
        #expect(SongLyricChords.deleted([c, g], at: 1) == [c, g])
    }

    @Test func aChordTypedWhileTransposedIsStoredUntransposed() {
        let text = "Hello there"
        // Stored C and G, shown two steps up as D and A.
        let stored = [SongChord.from(text: "C", characterNum: 0), SongChord.from(text: "G", characterNum: 6)]
        let shown = SongTranspose.shifted(stored, by: 2)
        #expect(SongText.displayedChordText(text: text, chords: shown, characterNum: 0) == "D")
        #expect(SongText.displayedChordText(text: text, chords: shown, characterNum: 6) == "A")
        #expect(SongText.displayedChordText(text: text, chords: shown, characterNum: 1) == nil)

        // The user types Em over the D. Stored is Dm, which draws as Em again.
        let edited = SongLyricChords.replaced(stored, at: 0, withText: "Em", steps: 2)
        #expect(edited[0].noteId == 2)
        #expect(edited[0].chordTypeId == 1)
        #expect(edited[1] == stored[1])
        let redrawn = SongTranspose.shifted(edited, by: 2)
        #expect(SongText.displayedChordText(text: text, chords: redrawn, characterNum: 0) == "Em")

        // A suffix this app does not know and a bass note shift with the root.
        let rich = SongLyricChords.replaced(stored, at: 6, withText: "Bmaj9/F#", steps: 2)
        #expect(rich[1].noteId == 9)
        #expect(rich[1].bassNoteId == 4)
        #expect(rich[1].suffix == "maj9")
        let shownRich = SongTranspose.shifted(rich, by: 2)
        #expect(SongText.displayedChordText(text: text, chords: shownRich, characterNum: 6) == "Bmaj9/F♯")

        // Text that is not a chord is an unrecognized chord that keeps its text, and no step changes it.
        let unknown = SongLyricChords.replaced(stored, at: 6, withText: "N.C.", steps: 5)
        #expect(unknown[1].unknown)
        #expect(SongText.displayedChordText(
            text: text, chords: SongTranspose.shifted(unknown, by: 5), characterNum: 6) == "N.C.")
    }

    @Test func movingAChordWhileTransposedKeepsItsStoredName() {
        let text = "Hello there"
        let stored = [SongChord.from(text: "C", characterNum: 0)]
        let moved = SongLyricChords.reattached(stored, from: 0, to: 3)
        #expect(moved[0].noteId == 0)
        #expect(SongText.displayedChordText(
            text: text, chords: SongTranspose.shifted(moved, by: 2), characterNum: 3) == "D")
    }

    @Test func theChordSheetPreviewsTheTypedText() {
        #expect(SongLyricChords.preview(ofTyped: "Bbm7") == "Shown as B♭m7")
        #expect(SongLyricChords.preview(ofTyped: "xyz") == "Not a chord. Start with a note from A to G.")
        #expect(SongLyricChords.preview(ofTyped: "") == "Not a chord. Start with a note from A to G.")
    }

    /// The chord sheet turns the field red and blocks OK and Return for text that is not a
    /// valid chord. Valid means a note A to G first, the same test transposing relies on.
    @Test func theChordSheetOnlyAcceptsValidChords() {
        for text in ["asdf", "", "   ", "?", "xyz", "N.C.", "m7"] {
            let entry = SongLyricChords.ChordEntry(text: text)
            #expect(entry.showsRed, "\(text)")
            #expect(!entry.canSave, "\(text)")
            #expect(entry.footer == "Not a chord. Start with a note from A to G.", "\(text)")
        }
        for text in ["C", "Bb", "F#m7/C#", "Em7/G", "Аm", "Сmaj7", "(Am)", "v:Am", "Gsus2add9"] {
            let entry = SongLyricChords.ChordEntry(text: text)
            #expect(!entry.showsRed, "\(text)")
            #expect(entry.canSave, "\(text)")
            #expect(entry.footer.hasPrefix("Shown as "), "\(text)")
        }
        // An empty chord shows "?", so it opens red.
        #expect(SongLyricChords.ChordEntry(text: "?").showsRed)
    }

    @Test func aSecondPressClearsTheSelectedLetter() {
        #expect(SongChordPick.action(
            selected: nil, hit: 4, pressedSelectedChord: true, selectedHasChord: true) == .select(4))
        #expect(SongChordPick.action(
            selected: 4, hit: 4, pressedSelectedChord: true, selectedHasChord: true) == .drag)
        #expect(SongChordPick.action(
            selected: 4, hit: 1, pressedSelectedChord: false, selectedHasChord: true) == .clear)
        #expect(SongChordPick.action(
            selected: 4, hit: nil, pressedSelectedChord: false, selectedHasChord: true) == .clear)
        // A letter with no chord can be selected, and a later press is not a drag.
        #expect(SongChordPick.action(
            selected: nil, hit: 2, pressedSelectedChord: false, selectedHasChord: false) == .select(2))
        #expect(SongChordPick.action(
            selected: 2, hit: 5, pressedSelectedChord: false, selectedHasChord: false) == .clear)
        #expect(SongChordPick.action(
            selected: nil, hit: nil, pressedSelectedChord: false, selectedHasChord: false) == nil)
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

    @Test func chordsWithNoLetterAreNotDrawnAndDoNotCrash() {
        // "ab\ncd": index 2 is the line break, 5 is the end, 99 is far past it.
        let text = "ab\ncd"
        let letters = [chord(at: 0, note: 0, type: 0), chord(at: 3, note: 7, type: 0)]
        for stray in [2, 5, 99, -1] {
            let chords = letters + [chord(at: stray, note: 3, type: 0)]
            let lines = SongText.sheet(text: text, chords: chords)
            #expect(lines[0].chords.map(\.anchor) == [0])
            #expect(lines[1].chords.map(\.anchor) == [0])
            let rendered = SongText.render(text: text, chords: chords, includeChords: true)
            #expect(rendered == "C\r\nab\r\nG\r\ncd")
        }
        // A name longer than its line is kept inside it.
        let long = SongText.render(text: "Oh", chords: [chord(at: 0, note: 0, type: 11)], includeChords: true)
        #expect(long.contains("\r\nOh"))
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

    /// Reset transpose goes back to the chords as they were opened. Shifting by 0 or by
    /// a whole octave (12, -12, 24) gives those same chords, and anything between does not.
    @Test func zeroAndWholeOctavesAreTheChordsAsOpened() {
        let chords = [
            SongChord(characterNum: 0, noteId: 4, chordTypeId: 1, bassNoteId: -1, marker: "", inParentheses: false),
            SongChord(characterNum: 5, noteId: 9, chordTypeId: 0, bassNoteId: 0, marker: "1", inParentheses: true),
        ]
        for steps in [0, 12, -12, 24, -24, 36] {
            #expect(SongTranspose.shifted(chords, by: steps) == chords, "\(steps)")
            #expect(!SongTranspose.changesChords(steps, in: chords), "\(steps)")
        }
        for steps in [1, 2, 7, -3, 11, -11, 13, -13] {
            #expect(SongTranspose.shifted(chords, by: steps) != chords, "\(steps)")
            #expect(SongTranspose.changesChords(steps, in: chords), "\(steps)")
        }
        #expect(SongTranspose.shifted(chords, by: 13) == SongTranspose.shifted(chords, by: 1))
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
    var hideFinished = false
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

    @Test func lettersAreNumberedAcrossLines() {
        let drawing = SongSheetLayout.drawing(for: [
            SongSheetLine(lyric: "Hi", chords: []),
            SongSheetLine(lyric: "", chords: []),
            SongSheetLine(lyric: "Yo", chords: [SongSheetChord(anchor: 1, text: "G")]),
        ])
        // A newline is a miss, so the second line starts at 3 and the third at 4.
        #expect(drawing.letters.map(\.characterNum) == [0, 1, 4, 5])
        let yo = drawing.letters[3]
        #expect(drawing.letter(at: CGPoint(x: yo.rect.midX, y: yo.rect.midY)) == 5)
        #expect(drawing.letter(at: CGPoint(x: yo.rect.maxX + 30, y: yo.rect.midY)) == nil)
    }

    @Test func aChordBoxIsCenteredOnItsLetter() {
        // A wide chord on the first letter pushes the sheet right. The letters move with it.
        let drawing = SongSheetLayout.drawing(for: [
            SongSheetLine(lyric: "Hello", chords: [SongSheetChord(anchor: 0, text: "Cmaj7/G")]),
        ])
        let box = drawing.chordBoxes[0]
        let letter = drawing.letters[0]
        #expect(box.characterNum == 0)
        #expect(abs(box.rect.midX - letter.rect.midX) < 0.01)
        #expect(box.rect.maxY <= letter.rect.minY + 4)
        #expect(box.rect.minX >= 16 - 0.01)
        #expect(letter.rect.minX > 16)
        let chord = drawing.glyphs.first { $0.text == "C" }
        #expect(chord != nil)
        #expect(abs(chord!.x - box.rect.minX) < 0.01)
    }

    @Test func aPressPicksTheSameLetterAtAnyZoom() {
        let drawing = SongSheetLayout.drawing(for: [
            SongSheetLine(lyric: "Hello there friend", chords: [SongSheetChord(anchor: 1, text: "Am")]),
        ])
        let letter = drawing.letters[12]
        let box = drawing.chordBoxes[0]
        for zoom: CGFloat in [0.25, 0.5, 1, 2, 3.5] {
            func at(_ x: CGFloat, _ y: CGFloat) -> CGPoint {
                CGPoint(x: x * zoom, y: y * zoom)
            }
            #expect(SongChordPick.action(
                in: drawing, at: at(letter.rect.midX, letter.rect.midY), zoom: zoom, selected: nil) == .select(12))
            #expect(SongChordPick.action(
                in: drawing, at: at(box.rect.midX, box.rect.midY), zoom: zoom, selected: nil) == .select(1))
            #expect(SongChordPick.action(
                in: drawing, at: at(box.rect.midX, box.rect.midY), zoom: zoom, selected: 1) == .drag)
            #expect(SongChordPick.action(
                in: drawing, at: at(letter.rect.midX, letter.rect.midY), zoom: zoom, selected: 12) == .edit)
            #expect(SongChordPick.action(
                in: drawing, at: at(letter.rect.midX, letter.rect.midY), zoom: zoom, selected: 1) == .clear)
            // Five screen points off the chord still count. Twelve do not.
            let near = CGPoint(x: box.rect.maxX * zoom + 5, y: box.rect.midY * zoom)
            #expect(SongChordPick.action(in: drawing, at: near, zoom: zoom, selected: 1) == .drag)
            let far = CGPoint(x: box.rect.maxX * zoom + 12, y: box.rect.midY * zoom)
            #expect(SongChordPick.action(in: drawing, at: far, zoom: zoom, selected: 1) == .clear)
            #expect(SongChordPick.action(in: drawing, at: far, zoom: zoom, selected: nil) == nil)
        }
    }

    @Test func theNearestLetterAcceptsAFingerInTheChordRow() {
        let drawing = SongSheetLayout.drawing(for: [
            SongSheetLine(lyric: "One", chords: [SongSheetChord(anchor: 0, text: "C")]),
            SongSheetLine(lyric: "Two", chords: []),
        ])
        let two = drawing.letters[3]
        #expect(drawing.nearestLetter(at: CGPoint(x: two.rect.midX, y: two.rect.midY)) == 4)
        let one = drawing.letters[1]
        let chordRow = CGPoint(x: one.rect.midX, y: one.reach.minY + 1)
        #expect(drawing.letter(at: chordRow) == nil)
        #expect(drawing.nearestLetter(at: chordRow) == 1)
        // Past the end of the line is a miss, so a drag there does not jump.
        #expect(drawing.nearestLetter(at: CGPoint(x: one.rect.maxX + 60, y: one.rect.midY)) == nil)
        // A finger far above the sheet still takes the first line.
        #expect(drawing.nearestLetter(at: CGPoint(x: one.rect.midX, y: -50)) == 1)
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
                characterNum: 0, noteId: 0, chordTypeId: 0, bassNoteId: 4, marker: "1", inParentheses: true,
                rootText: "C", bassText: "E"),
        ])

        #expect(sheet == [SongSheetLine(lyric: "Hello", chords: [SongSheetChord(anchor: 0, text: "C")])])

        #expect(throws: SongbookError.songNotFound) {
            try Songbook.sheet(id: 99, in: url)
        }
    }

    @Test func refusesAnOldFormatSongbook() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("songbook-\(UUID().uuidString).songbook")
        defer { try? FileManager.default.removeItem(at: url) }
        try writeSongbook(at: url, version: 0)
        #expect(throws: SongbookError.oldFormat) {
            try Songbook.titles(in: url)
        }
        try writeSongbook(at: url, version: 3)
        #expect(throws: SongbookError.newerFormat(3)) {
            try Songbook.titles(in: url)
        }
    }

    @Test func unreadableChordStringsBecomeUnknownChords() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("songbook-\(UUID().uuidString).songbook")
        defer { try? FileManager.default.removeItem(at: url) }
        try writeSongbook(at: url)
        try withTestDatabase(url) { db in
            try exec(
                db,
                """
                INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (2, 6, 'N.C.');
                INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (2, 7, '');
                """)
        }
        let source = try Songbook.source(id: 2, in: url)
        #expect(source.chords.count == 3)
        #expect(source.chords[1].unknown)
        #expect(source.chords[1].raw == "N.C.")
        #expect(source.chords.dropFirst().allSatisfy { $0.unknown })
        let text = try Songbook.songText(id: 2, includeChords: true, in: url)
        #expect(text.contains("N."))
        // Moving an unknown chord keeps it unknown.
        let moved = SongLyricChords.reattached(source.chords, from: 6, to: 3)
        #expect(moved.contains { $0.characterNum == 3 && $0.unknown })
    }
}

struct ChordParserTests {
    @Test func sharedVectors() throws {
        let url = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("tests/chord_vectors.json")
        let data = try Data(contentsOf: url)
        let root = try #require(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let cases = try #require(root["cases"] as? [[String: Any]])
        #expect(cases.count > 100)
        for item in cases {
            let input = item["input"] as? String ?? ""
            let parsed = SoftchordChords.parseChord(input)
            let unknown = item["unknown"] as? Bool ?? false
            #expect(parsed.unknown == unknown, "\(input)")
            #expect(SoftchordChords.parsedChordString(parsed) == item["canonical"] as? String, "\(input)")
            if unknown {
                let display = item["display"] as? String
                #expect(parsed.display == display, "\(input)")
                #expect(SoftchordChords.unrecognizedChordDisplay(input) == display, "\(input)")
                let made = SongChord.from(text: input, characterNum: 0)
                #expect(SoftchordChords.chordText(made, prefer: 0) == display, "\(input)")
                continue
            }
            #expect(item["display"] == nil, "\(input)")
            #expect(parsed.rootText == item["root"] as? String, "\(input)")
            #expect(parsed.noteId == item["note_id"] as? Int, "\(input)")
            #expect((parsed.isMinor ? "minor" : "major") == item["quality"] as? String, "\(input)")
            #expect(parsed.chordTypeId == item["type_id"] as? Int, "\(input)")
            #expect(parsed.isKnownType == item["known_type"] as? Bool, "\(input)")
            #expect(parsed.suffix == item["suffix"] as? String, "\(input)")
            #expect((parsed.bassText.isEmpty ? nil : parsed.bassText) == item["bass"] as? String, "\(input)")
            if item["bass"] as? String != nil {
                #expect(parsed.bassNoteId == item["bass_id"] as? Int, "\(input)")
            }
            #expect(parsed.marker == item["marker"] as? String, "\(input)")
            #expect(parsed.inParentheses == item["parens"] as? Bool, "\(input)")
            // The canonical string reads back as itself.
            let canonical = SoftchordChords.parsedChordString(parsed)
            #expect(SoftchordChords.parsedChordString(SoftchordChords.parseChord(canonical)) == canonical, "\(input)")
        }
    }

    @Test func sharedValidityVectors() throws {
        let url = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("tests/chord_vectors.json")
        let root = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
        let validity = try #require(root["validity"] as? [String: Any])
        let valid = try #require(validity["valid"] as? [String])
        let invalid = try #require(validity["invalid"] as? [String])
        #expect(valid.count > 10)
        for text in valid {
            #expect(SoftchordChords.isValidChordText(text), "\(text)")
        }
        for text in invalid {
            #expect(!SoftchordChords.isValidChordText(text), "\(text)")
        }
    }

    @Test func validChordTextIsWhatTransposingChanges() {
        for text in ["C", "Am", "Em7/G", "Bb", "F#m7/C#", "H", "Аm", "(Am)", "v:Am", "Gsus2add9",
                     "asdf", "", "?", "xyz", "N.C."] {
            let chord = SongChord.from(text: text, characterNum: 0)
            let moved = SongTranspose.shifted([chord], by: 1)[0]
            #expect(SoftchordChords.isValidChordText(text) == (moved != chord), "\(text)")
        }
    }

    @Test func garbageNeverCrashes() {
        for text in ["", "   ", "?", "(", ")", "()", ":", "/", "C/", "/C", "(:)", "\u{0}", "💥", "C/H/", "((C))"] {
            _ = SoftchordChords.parseChord(text)
            _ = SongChord.from(text: text, characterNum: 0)
        }
    }

    @Test func unknownSuffixIsKeptAndSurvivesTranspose() {
        let chord = SongChord.from(text: "Am7add13/G", characterNum: 0)
        #expect(!chord.unknown)
        #expect(chord.chordTypeId == 1)
        #expect(SoftchordChords.chordText(chord, prefer: 0) == "Am7add13/G")
        let up = SongTranspose.shifted([chord], by: 2)
        #expect(SoftchordChords.chordText(up[0], prefer: 0) == "Bm7add13/A")
        let unknown = SongChord.from(text: "N.C.", characterNum: 0)
        #expect(SongTranspose.shifted([unknown], by: 2) == [unknown])
        #expect(SoftchordChords.chordText(unknown, prefer: 0) == "N.C.")
    }

    @Test func onlyTextThatIsNotAChordIsCutToSevenCharacters() {
        func shown(_ text: String) -> String {
            SoftchordChords.chordText(SongChord.from(text: text, characterNum: 0), prefer: 0)
        }
        #expect(shown("abcdefghij") == "abcdefg")
        #expect(shown("  asdf ") == "asdf")
        #expect(shown("Пожалуйста") == "Пожалуй")
        #expect(shown("🎵🎵🎵🎵🎵🎵🎵🎵") == "🎵🎵🎵🎵🎵🎵🎵")
        #expect(shown("") == "?")
        #expect(shown("?") == "?")
        // A real chord is shown in full, spelled as it is.
        #expect(shown("Cmaj7sus4add9/F#") == "Cmaj7sus4add9/F♯")
    }

    @Test func unrecognizedChordsAreRedInTheSheetAndTheImage() {
        let chords = [
            SongChord.from(text: "C", characterNum: 0),
            SongChord.from(text: "abcdefghij", characterNum: 4),
        ]
        let sheet = SongText.sheet(text: "abc def", chords: chords)
        #expect(sheet[0].chords.map(\.text) == ["C", "abcdefg"])
        #expect(sheet[0].chords.map(\.unrecognized) == [false, true])
        let drawing = SongSheetLayout.drawing(for: sheet)
        func color(of letter: String) -> [CGFloat]? {
            drawing.glyphs.first { $0.text == letter && $0.baseline < drawing.glyphs[0].baseline }
                .flatMap { $0.color.components }
        }
        #expect(color(of: "C") == [0, 0, 1, 1])
        #expect(color(of: "a") == [1, 0, 0, 1])
        #expect(color(of: "g") == [1, 0, 0, 1])
        #expect(!drawing.glyphs.contains { $0.text == "h" })
    }

    @Test func transposingASongWithNoMovableChordChangesNothing() {
        let unrecognized = SongChord.from(text: "N.C.", characterNum: 0)
        let real = SongChord.from(text: "Am", characterNum: 4)
        #expect(!SongTranspose.changesChords(1, in: [unrecognized]))
        #expect(!SongTranspose.changesChords(1, in: []))
        #expect(SongTranspose.changesChords(1, in: [unrecognized, real]))
        #expect(!SongTranspose.changesChords(12, in: [unrecognized, real]))
        #expect(!SongTranspose.changesChords(-24, in: [unrecognized, real]))
        #expect(SongTranspose.changesChords(13, in: [real]))
    }

    @Test func unknownChordsDoNotChangeTheKeyOrCrashRendering() {
        let chords = [
            SongChord.from(text: "N.C.", characterNum: 0),
            SongChord.from(text: "C", characterNum: 2),
        ]
        let text = SongText.render(text: "abc def", chords: chords, includeChords: true)
        #expect(text.contains("N.C."))
        #expect(text.contains("C"))
        let sheet = SongText.sheet(text: "abc def", chords: chords)
        #expect(sheet.first?.chords.map(\.text) == ["N.C.", "C"])
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

private func withTestDatabase(_ url: URL, _ body: (OpaquePointer) throws -> Void) throws {
    var db: OpaquePointer?
    if sqlite3_open(url.path, &db) != SQLITE_OK {
        throw SongbookError.openFailed("Could not open the test songbook.")
    }
    guard let db else {
        throw SongbookError.openFailed("Could not open the test songbook.")
    }
    defer { sqlite3_close(db) }
    try body(db)
}

/// `version` is the PRAGMA user_version, 2 unless a test needs another.
private func writeSongbook(at url: URL, version: Int = 2) throws {
    try? FileManager.default.removeItem(at: url)
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
        INSERT INTO songs (id, uuid, text, title, updated_at) VALUES (2, '2b0f0a5e-6f38-4d0b-9d6e-6c1d9a6e1b02', 'Hello world', 'beta Song', 1700000000);
        INSERT INTO songs (id, uuid, text, title, updated_at) VALUES (1, '5d1c3f0a-1c52-4a43-8f55-0a8d2f6f3a01', 'Hello', 'Alpha', 1700000001);
        INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (1, 0, 'C');
        INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (2, 0, '(1:C/E)');
        PRAGMA user_version = \(version);
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

struct LyricChordMoveTests {
    private func chord(_ index: Int) -> SongChord {
        SongChord(
            characterNum: index, noteId: index % 12, chordTypeId: 0, bassNoteId: -1, marker: "",
            inParentheses: false)
    }

    private func indices(_ chords: [SongChord]) -> [Int] {
        chords.map(\.characterNum)
    }

    @Test func deletingOneOfTwoRepeatedLettersKeepsOneChordPerLetter() {
        let all = (0..<5).map(chord)
        let moved = SongLyricChords.moved(all, from: "Hello", to: "Helo")
        #expect(indices(moved) == [0, 1, 2, 3])
        #expect(moved.map(\.noteId) == [0, 1, 2, 4])

        let aab = SongLyricChords.moved((0..<3).map(chord), from: "aab", to: "ab")
        #expect(indices(aab) == [0, 1])
        #expect(aab.map(\.noteId) == [0, 2])
    }

    @Test func typingARepeatedLetterKeepsEveryChord() {
        #expect(indices(SongLyricChords.moved((0..<2).map(chord), from: "aa", to: "aaa")) == [0, 1])
        #expect(indices(SongLyricChords.moved((0..<5).map(chord), from: "Hello", to: "Helllo")) == [0, 1, 2, 3, 5])
    }

    @Test func sharedLyricChordVectors() throws {
        let url = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("tests/lyric_chord_vectors.json")
        let root = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
        let cases = try #require(root["cases"] as? [[String: Any]])
        #expect(cases.count > 30)
        for item in cases {
            let name = item["name"] as? String ?? ""
            let old = item["old"] as? String ?? ""
            let new = item["new"] as? String ?? ""
            let chordsIn = item["chords_in"] as? [Int] ?? []
            let kept = item["kept"] as? [Int] ?? []
            let expected = item["chords_out"] as? [Int] ?? []
            let moved = SongLyricChords.moved(chordsIn.map(chord), from: old, to: new)
            #expect(indices(moved) == expected, "\(name)")
            // The chord that is kept is the one that was on that letter.
            #expect(moved.map(\.noteId) == kept.map { $0 % 12 }, "\(name)")
        }
    }

    @Test func randomEditsKeepTheRules() {
        var generator = SystemRandomNumberGenerator()
        let alphabet: [Character] = ["a", "b", "\n", "Ж", "😀", " "]
        func randomText(_ count: Int) -> String {
            String((0..<count).map { _ in alphabet.randomElement(using: &generator)! })
        }
        for _ in 0..<1000 {
            let old = randomText(Int.random(in: 0...9, using: &generator))
            let oldScalars = Array(old.unicodeScalars)
            let start = Int.random(in: 0...oldScalars.count, using: &generator)
            let end = Int.random(in: start...oldScalars.count, using: &generator)
            var scalars = oldScalars
            scalars.replaceSubrange(start..<end, with: Array(randomText(Int.random(in: 0...4, using: &generator)).unicodeScalars))
            var view = String.UnicodeScalarView()
            view.append(contentsOf: scalars)
            let new = String(view)
            let newScalars = Array(new.unicodeScalars)
            let moved = SongLyricChords.moved((0..<oldScalars.count).map(chord), from: old, to: new)
            let targets = indices(moved)
            #expect(Set(targets).count == targets.count, "\(old) -> \(new)")
            #expect(targets == targets.sorted(), "\(old) -> \(new)")
            for chord in moved {
                // Old text is at most 9 letters, so the note id is the old index.
                #expect(chord.characterNum < newScalars.count, "\(old) -> \(new)")
                #expect(oldScalars[chord.noteId] == newScalars[chord.characterNum], "\(old) -> \(new)")
            }
            #expect(moved.count >= oldScalars.count - (end - start), "\(old) -> \(new)")
        }
    }
}

struct ChordJumpTests {
    private func chord(_ index: Int, note: Int = 0) -> SongChord {
        SongChord(
            characterNum: index, noteId: note, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false)
    }

    private func vectors() throws -> [String: Any] {
        let url = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("tests/chord_move_vectors.json")
        return try #require(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
    }

    @Test func sharedJumpVectors() throws {
        let cases = try #require(vectors()["jumps"] as? [[String: Any]])
        #expect(cases.count > 20)
        for item in cases {
            let name = item["name"] as? String ?? ""
            let landing = SongLyricChords.nextFreeCharacter(
                in: item["text"] as? String ?? "",
                target: item["target"] as? Int ?? 0,
                direction: item["direction"] as? Int ?? 1,
                occupied: Set(item["occupied"] as? [Int] ?? []),
                allowOtherDirection: item["allow_other_direction"] as? Bool ?? false)
            #expect(landing == item["expected"] as? Int, "\(name)")
        }
    }

    @Test func sharedDirectionVectors() throws {
        let cases = try #require(vectors()["directions"] as? [[String: Any]])
        #expect(cases.count > 5)
        for item in cases {
            let name = item["name"] as? String ?? ""
            let direction = SongLyricChords.dragDirection(
                in: item["text"] as? String ?? "",
                chord: item["chord"] as? Int ?? 0,
                previous: item["previous"] as? Int ?? 0,
                target: item["target"] as? Int ?? 0)
            #expect(direction == item["expected"] as? Int, "\(name)")
        }
    }

    @Test func aJumpLandsOnAFreeLetterOfTheSameLine() {
        var generator = SystemRandomNumberGenerator()
        for _ in 0..<1000 {
            let letters = (0..<Int.random(in: 0...9, using: &generator)).map { _ in
                ["a", "b", "\n"].randomElement(using: &generator)!
            }
            let text = letters.joined()
            let occupied = Set((0..<letters.count).filter { _ in Bool.random(using: &generator) })
            let target = Int.random(in: -1...letters.count, using: &generator)
            let direction = Bool.random(using: &generator) ? 1 : -1
            let other = Bool.random(using: &generator)
            guard let landing = SongLyricChords.nextFreeCharacter(
                in: text, target: target, direction: direction, occupied: occupied, allowOtherDirection: other)
            else {
                continue
            }
            #expect(!occupied.contains(landing), "\(text)")
            #expect(letters[landing] != "\n", "\(text)")
            let low = min(landing, target)
            let high = max(landing, target)
            #expect(!letters[low..<high].contains("\n"), "\(text)")
        }
    }

    @Test func aMovedChordNeverSharesALetterOrLosesAChord() {
        let chords = [chord(1, note: 1), chord(2, note: 2), chord(4, note: 4)]
        let landing = SongLyricChords.nextFreeCharacter(
            in: "0123456789", target: 2, direction: 1, occupied: [2, 4], allowOtherDirection: true)
        #expect(landing == 3)
        let moved = SongLyricChords.reattached(chords, from: 1, to: landing ?? 1)
        #expect(moved.map(\.characterNum) == [3, 2, 4])
        #expect(moved.map(\.noteId) == [1, 2, 4])
        // The first letter of a full line cannot take another chord.
        let full = [chord(0), chord(1), chord(2)]
        #expect(SongLyricChords.reattached(full, from: 0, to: 2) == full)
    }

    @Test func draggingOverSeveralChordsAndBackFollowsTheFinger() {
        // The page drives a drag like this: the finger is over a letter, the chord
        // lands on the next free letter, and the finger stays on the occupied one.
        let text = "0123456789"
        var chords = [chord(1, note: 1), chord(2, note: 2), chord(3, note: 3)]
        var chordAt = 1
        var finger = 1
        func drag(to target: Int) {
            guard target != finger else {
                return
            }
            let occupied = Set(chords.map(\.characterNum)).subtracting([chordAt])
            let direction = SongLyricChords.dragDirection(in: text, chord: chordAt, previous: finger, target: target)
            finger = target
            if let to = SongLyricChords.nextFreeCharacter(
                in: text, target: target, direction: direction, occupied: occupied, allowOtherDirection: true),
               to != chordAt {
                chords = SongLyricChords.reattached(chords, from: chordAt, to: to)
                chordAt = to
            }
        }
        drag(to: 2)
        #expect(chordAt == 4)
        drag(to: 2)
        #expect(chordAt == 4)
        drag(to: 3)
        #expect(chordAt == 4)
        drag(to: 5)
        #expect(chordAt == 5)
        drag(to: 3)
        #expect(chordAt == 1)
        #expect(chords.map(\.characterNum).sorted() == [1, 2, 3])
        #expect(Set(chords.map(\.noteId)) == [1, 2, 3])
    }
}
