//
//  SongPhotoLibrary.swift
//  softChord Viewer
//

import Photos
import UIKit

enum SongPhotoLibrary {
    enum Failure: Error, CustomStringConvertible {
        case denied
        case saveFailed(String)

        var description: String {
            switch self {
            case .denied:
                return "Photos access is turned off for softChord Viewer."
            case .saveFailed(let message):
                return message
            }
        }
    }

    /// Saves a song sheet with add-only Photos access.
    static func add(_ image: UIImage) async throws {
        let status = await PHPhotoLibrary.requestAuthorization(for: .addOnly)
        guard status == .authorized || status == .limited else {
            throw Failure.denied
        }
        do {
            try await PHPhotoLibrary.shared().performChanges {
                PHAssetChangeRequest.creationRequestForAsset(from: image)
            }
        } catch {
            throw Failure.saveFailed(error.localizedDescription)
        }
    }
}
