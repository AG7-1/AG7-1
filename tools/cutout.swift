// Removes the background from a portrait using macOS Vision (no downloads needed).
// usage: swift tools/cutout.swift photo_original.jpg photo.png
import AppKit
import CoreImage
import Vision

let args = CommandLine.arguments
guard args.count == 3, let src = CIImage(contentsOf: URL(fileURLWithPath: args[1])) else {
    print("usage: swift cutout.swift <in.jpg> <out.png>"); exit(1)
}

let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8
try VNImageRequestHandler(ciImage: src).perform([req])
guard let maskBuf = req.results?.first?.pixelBuffer else { print("no person found"); exit(1) }

var mask = CIImage(cvPixelBuffer: maskBuf)
mask = mask.transformed(by: CGAffineTransform(
    scaleX: src.extent.width / mask.extent.width,
    y: src.extent.height / mask.extent.height))

let clear = CIImage(color: .clear).cropped(to: src.extent)
let out = src.applyingFilter("CIBlendWithMask", parameters: [
    kCIInputBackgroundImageKey: clear, kCIInputMaskImageKey: mask])

let ctx = CIContext()
try ctx.writePNGRepresentation(of: out, to: URL(fileURLWithPath: args[2]),
                               format: .RGBA8, colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!)
print("wrote \(args[2])")
