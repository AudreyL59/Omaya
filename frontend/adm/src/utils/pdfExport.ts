// Export PDF depuis un element DOM via html2canvas-pro + jsPDF.
// Pagine automatiquement si le contenu est plus haut qu'une page A4.

import jsPDF from 'jspdf'
import html2canvas from 'html2canvas-pro'

export async function exportElementToPDF(
  element: HTMLElement,
  filename: string,
  title?: string,
): Promise<void> {
  // Rendu canvas haute resolution
  const canvas = await html2canvas(element, {
    scale: 2,             // meilleure qualite
    backgroundColor: '#ffffff',
    useCORS: true,
    logging: false,
  })

  const imgData = canvas.toDataURL('image/png')
  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
    compress: true,
  })

  // Dimensions A4 : 210 x 297 mm. Marges 10mm
  const pageWidth = 210
  const pageHeight = 297
  const margin = 10
  const contentWidth = pageWidth - margin * 2

  // Ratio d'echelle
  const imgWidth = contentWidth
  const imgHeight = (canvas.height * imgWidth) / canvas.width

  // Titre (optionnel) en haut de la premiere page
  let yOffset = margin
  if (title) {
    pdf.setFontSize(14)
    pdf.setFont('helvetica', 'bold')
    pdf.text(title, margin, yOffset + 4)
    yOffset += 10
  }

  // Si l'image tient sur une page
  const usableHeight = pageHeight - yOffset - margin
  if (imgHeight <= usableHeight) {
    pdf.addImage(imgData, 'PNG', margin, yOffset, imgWidth, imgHeight)
  } else {
    // Pagination : on decoupe l'image en morceaux
    let remaining = imgHeight
    let srcY = 0
    let firstPage = true
    while (remaining > 0) {
      const sliceTopMargin = firstPage ? yOffset : margin
      const sliceHeight = Math.min(
        remaining,
        pageHeight - sliceTopMargin - margin
      )
      // Portion de canvas a utiliser
      const srcHeight = (sliceHeight * canvas.width) / imgWidth
      const sliceCanvas = document.createElement('canvas')
      sliceCanvas.width = canvas.width
      sliceCanvas.height = srcHeight
      const ctx = sliceCanvas.getContext('2d')
      if (ctx) {
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, sliceCanvas.width, sliceCanvas.height)
        ctx.drawImage(canvas, 0, -srcY)
      }
      const sliceImg = sliceCanvas.toDataURL('image/png')
      pdf.addImage(sliceImg, 'PNG', margin, sliceTopMargin, imgWidth, sliceHeight)

      remaining -= sliceHeight
      srcY += srcHeight
      if (remaining > 0) {
        pdf.addPage()
        firstPage = false
      }
    }
  }

  pdf.save(filename.endsWith('.pdf') ? filename : `${filename}.pdf`)
}
