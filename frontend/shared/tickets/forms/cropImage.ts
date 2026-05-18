// Génère une image recadrée (data URL JPEG) à partir de la source,
// de la zone de crop (pixels) et d'une rotation — pattern standard
// react-easy-crop.

export interface PixelCrop {
  x: number
  y: number
  width: number
  height: number
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.addEventListener('load', () => resolve(img))
    img.addEventListener('error', (e) => reject(e))
    img.src = src
  })
}

export async function getCroppedDataUrl(
  imageSrc: string,
  crop: PixelCrop,
  rotation = 0,
): Promise<string> {
  const image = await loadImage(imageSrc)
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Canvas non supporté')

  const rad = (rotation * Math.PI) / 180

  // Canvas intermédiaire pour appliquer la rotation autour du centre
  const bBoxW =
    Math.abs(Math.cos(rad) * image.width) +
    Math.abs(Math.sin(rad) * image.height)
  const bBoxH =
    Math.abs(Math.sin(rad) * image.width) +
    Math.abs(Math.cos(rad) * image.height)

  const rotCanvas = document.createElement('canvas')
  const rotCtx = rotCanvas.getContext('2d')
  if (!rotCtx) throw new Error('Canvas non supporté')
  rotCanvas.width = bBoxW
  rotCanvas.height = bBoxH
  rotCtx.translate(bBoxW / 2, bBoxH / 2)
  rotCtx.rotate(rad)
  rotCtx.drawImage(image, -image.width / 2, -image.height / 2)

  canvas.width = crop.width
  canvas.height = crop.height
  ctx.drawImage(
    rotCanvas,
    crop.x,
    crop.y,
    crop.width,
    crop.height,
    0,
    0,
    crop.width,
    crop.height,
  )
  return canvas.toDataURL('image/jpeg', 0.92)
}
