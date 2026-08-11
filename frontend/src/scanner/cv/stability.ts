export class StabilityTracker {
  private history: { cx: number, cy: number, area: number }[] = [];
  private windowSize: number;

  constructor(windowSize: number = 3) {
    this.windowSize = windowSize;
  }

  public push(cx: number, cy: number, area: number): boolean {
    this.history.push({ cx, cy, area });
    if (this.history.length > this.windowSize) {
      this.history.shift();
    }
    return this.isStable();
  }

  public reset() {
    this.history = [];
  }

  public isStable(): boolean {
    if (this.history.length < this.windowSize) return false;

    // Calculate max variance
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    let minArea = Infinity, maxArea = -Infinity;

    for (const h of this.history) {
      if (h.cx < minX) minX = h.cx;
      if (h.cx > maxX) maxX = h.cx;
      if (h.cy < minY) minY = h.cy;
      if (h.cy > maxY) maxY = h.cy;
      if (h.area < minArea) minArea = h.area;
      if (h.area > maxArea) maxArea = h.area;
    }

    const shiftX = maxX - minX;
    const shiftY = maxY - minY;
    
    // Config thresholds
    const maxShiftPx = 10;
    const maxAreaVariance = 0.05; // 5%

    const avgArea = (minArea + maxArea) / 2;
    const areaVariance = (maxArea - minArea) / (avgArea || 1);

    return shiftX <= maxShiftPx && shiftY <= maxShiftPx && areaVariance <= maxAreaVariance;
  }
}
