/**
 * Generateur PDF A4 (portrait) contenant une ou plusieurs images
 * cadrees, avec (optionnel) un filigrane "SPECIMEN" tuile en rouge
 * transparent — reproduction du filigrane genere cote Flutter dans
 * les fenetres Ticket Call Energie + Fibre (PDF de CIN, KBIS,
 * Clarification, Justif ...).
 *
 * Utilise pdf-lib.
 */

import {
  PDFDocument, PDFPage, rgb, StandardFonts, degrees,
} from 'pdf-lib'

const A4_WIDTH = 595.28
const A4_HEIGHT = 841.89

/**
 * Genere un PDF A4 avec les images passees en entree (une par page).
 * @param images   Liste de blobs/File images (jpeg, png, etc.)
 * @param options  filigrane: applique le filigrane SPECIMEN si true.
 * @returns bytes PDF (Uint8Array)
 */
export async function generateImagesPdf(
  images: (Blob | File | ArrayBuffer)[],
  options: { filigrane?: boolean } = {},
): Promise<Uint8Array> {
  const { filigrane = false } = options
  const pdfDoc = await PDFDocument.create()
  const font = filigrane
    ? await pdfDoc.embedFont(StandardFonts.HelveticaBold)
    : null

  for (const img of images) {
    const bytes = img instanceof ArrayBuffer
      ? new Uint8Array(img)
      : new Uint8Array(await (img as Blob).arrayBuffer())
    // Detection JPEG vs PNG (2 signatures)
    const sig4 = bytes.slice(0, 4)
    const isJpeg = sig4[0] === 0xff && sig4[1] === 0xd8
    const embed = isJpeg
      ? await pdfDoc.embedJpg(bytes)
      : await pdfDoc.embedPng(bytes)

    const page = pdfDoc.addPage([A4_WIDTH, A4_HEIGHT])
    // Cadre l'image dans la page en gardant les proportions
    const scale = Math.min(A4_WIDTH / embed.width, A4_HEIGHT / embed.height)
    const w = embed.width * scale
    const h = embed.height * scale
    page.drawImage(embed, {
      x: (A4_WIDTH - w) / 2,
      y: (A4_HEIGHT - h) / 2,
      width: w,
      height: h,
    })

    if (filigrane && font) {
      _drawFiligraneSpecimen(page, font)
    }
  }
  return pdfDoc.save()
}


/**
 * Filigrane SPECIMEN tuile en rouge transparent, incline -45°.
 * Reproduit les parametres Flutter :
 *   couleur rouge, opacite 0.5, rotation -0.785 rad (~45°),
 *   fontSize 36, tuilage 150 x 250.
 */
function _drawFiligraneSpecimen(page: PDFPage, font: any) {
  const step_x = 150
  const step_y = 250
  const fontSize = 36
  const color = rgb(1, 0, 0)
  const opacity = 0.35
  const rotation = degrees(45)

  for (let y = -step_y; y < A4_HEIGHT + step_y; y += step_y) {
    for (let x = -step_x; x < A4_WIDTH + step_x; x += step_x) {
      page.drawText('SPECIMEN', {
        x, y,
        font, size: fontSize,
        color, opacity,
        rotate: rotation,
      })
    }
  }
}


/**
 * Utilitaire : lit un File en tableau d'octets.
 */
export async function fileToBytes(file: File | Blob): Promise<Uint8Array> {
  return new Uint8Array(await file.arrayBuffer())
}
