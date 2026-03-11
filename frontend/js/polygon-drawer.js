/**
 * PolygonDrawer - Canvas-based polygon drawing for parking space definition
 */
class PolygonDrawer {
    constructor(canvasId, options = {}) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');

        // Configuration
        this.options = {
            pointRadius: 6,
            lineWidth: 2,
            fillAlpha: 0.3,
            colors: {
                drawing: '#3498db',
                completed: '#2ecc71',
                selected: '#e74c3c',
                hover: '#f39c12'
            },
            ...options
        };

        // State
        this.backgroundImage = null;
        this.originalWidth = 0;
        this.originalHeight = 0;
        this.scaleX = 1;
        this.scaleY = 1;

        this.polygons = [];
        this.currentPoints = [];
        this.selectedIndex = -1;
        this.hoveredIndex = -1;
        this.isDragging = false;
        this.dragPointIndex = -1;

        // Callbacks
        this.onPolygonComplete = options.onPolygonComplete || null;
        this.onPolygonSelect = options.onPolygonSelect || null;
        this.onChange = options.onChange || null;

        this._bindEvents();
    }

    /**
     * Set the background image (video frame)
     */
    setBackgroundImage(imageDataUrl, originalWidth, originalHeight) {
        const img = new Image();
        img.onload = () => {
            this.backgroundImage = img;
            this.originalWidth = originalWidth;
            this.originalHeight = originalHeight;
            this._resizeCanvas();
            this._render();
        };
        img.src = imageDataUrl;
    }

    /**
     * Resize canvas to fit container
     */
    _resizeCanvas() {
        const container = this.canvas.parentElement;
        const containerWidth = container.clientWidth;
        const maxHeight = window.innerHeight * 0.6;

        const aspectRatio = this.originalWidth / this.originalHeight;
        let width = containerWidth;
        let height = width / aspectRatio;

        if (height > maxHeight) {
            height = maxHeight;
            width = height * aspectRatio;
        }

        this.canvas.width = width;
        this.canvas.height = height;

        this.scaleX = this.originalWidth / width;
        this.scaleY = this.originalHeight / height;
    }

    /**
     * Convert canvas coordinates to original image coordinates
     */
    canvasToOriginal(x, y) {
        return [
            Math.round(x * this.scaleX),
            Math.round(y * this.scaleY)
        ];
    }

    /**
     * Convert original image coordinates to canvas coordinates
     */
    originalToCanvas(x, y) {
        return [
            x / this.scaleX,
            y / this.scaleY
        ];
    }

    /**
     * Bind event listeners
     */
    _bindEvents() {
        this.canvas.addEventListener('click', this._handleClick.bind(this));
        this.canvas.addEventListener('dblclick', this._handleDoubleClick.bind(this));
        this.canvas.addEventListener('mousemove', this._handleMouseMove.bind(this));
        this.canvas.addEventListener('mousedown', this._handleMouseDown.bind(this));
        this.canvas.addEventListener('mouseup', this._handleMouseUp.bind(this));

        document.addEventListener('keydown', this._handleKeyDown.bind(this));

        window.addEventListener('resize', () => {
            if (this.backgroundImage) {
                this._resizeCanvas();
                this._render();
            }
        });
    }

    /**
     * Get mouse position relative to canvas
     */
    _getMousePos(event) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top
        };
    }

    /**
     * Handle click - add point or select polygon
     */
    _handleClick(event) {
        const pos = this._getMousePos(event);

        // If not currently drawing, check for polygon selection
        if (this.currentPoints.length === 0) {
            const clickedIndex = this._findPolygonAtPoint(pos.x, pos.y);
            if (clickedIndex !== -1) {
                this.selectedIndex = clickedIndex;
                if (this.onPolygonSelect) {
                    this.onPolygonSelect(this.polygons[clickedIndex], clickedIndex);
                }
                this._render();
                return;
            }
        }

        // Deselect if clicking empty area
        if (this.selectedIndex !== -1 && this.currentPoints.length === 0) {
            this.selectedIndex = -1;
            if (this.onPolygonSelect) {
                this.onPolygonSelect(null, -1);
            }
        }

        // Add point to current polygon
        this.currentPoints.push([pos.x, pos.y]);
        this._render();
        this._notifyChange();
    }

    /**
     * Handle double-click - complete polygon
     */
    _handleDoubleClick(event) {
        event.preventDefault();
        this._completeCurrentPolygon();
    }

    /**
     * Handle mouse move - update hover state and preview
     */
    _handleMouseMove(event) {
        const pos = this._getMousePos(event);

        // Update hover state
        if (this.currentPoints.length === 0) {
            const hoverIndex = this._findPolygonAtPoint(pos.x, pos.y);
            if (hoverIndex !== this.hoveredIndex) {
                this.hoveredIndex = hoverIndex;
                this.canvas.style.cursor = hoverIndex !== -1 ? 'pointer' : 'crosshair';
                this._render();
            }
        } else {
            this.canvas.style.cursor = 'crosshair';
        }

        // Handle point dragging
        if (this.isDragging && this.dragPointIndex !== -1 && this.selectedIndex !== -1) {
            const polygon = this.polygons[this.selectedIndex];
            polygon.points[this.dragPointIndex] = this.canvasToOriginal(pos.x, pos.y);
            this._render();
        }

        // Redraw to show preview line to cursor
        if (this.currentPoints.length > 0) {
            this._render();
            this._drawPreviewLine(pos.x, pos.y);
        }
    }

    /**
     * Handle mouse down - start point dragging
     */
    _handleMouseDown(event) {
        if (this.selectedIndex === -1) return;

        const pos = this._getMousePos(event);
        const polygon = this.polygons[this.selectedIndex];

        for (let i = 0; i < polygon.points.length; i++) {
            const [px, py] = this.originalToCanvas(...polygon.points[i]);
            const dist = Math.hypot(pos.x - px, pos.y - py);
            if (dist < this.options.pointRadius + 4) {
                this.isDragging = true;
                this.dragPointIndex = i;
                return;
            }
        }
    }

    /**
     * Handle mouse up - end point dragging
     */
    _handleMouseUp(event) {
        if (this.isDragging) {
            this.isDragging = false;
            this.dragPointIndex = -1;
            this._notifyChange();
        }
    }

    /**
     * Handle keyboard events
     */
    _handleKeyDown(event) {
        if (event.key === 'Enter') {
            this._completeCurrentPolygon();
        } else if (event.key === 'Escape') {
            this.cancelCurrentPolygon();
        } else if (event.key === 'Delete' && this.selectedIndex !== -1) {
            this.deleteSelected();
        }
    }

    /**
     * Complete the current polygon
     */
    _completeCurrentPolygon() {
        if (this.currentPoints.length < 3) {
            return;
        }

        const originalPoints = this.currentPoints.map(([x, y]) =>
            this.canvasToOriginal(x, y)
        );

        const polygon = {
            points: originalPoints,
            name: `Space ${this.polygons.length + 1}`
        };

        this.polygons.push(polygon);
        this.currentPoints = [];
        this.selectedIndex = this.polygons.length - 1;

        if (this.onPolygonComplete) {
            this.onPolygonComplete(polygon, this.selectedIndex);
        }

        this._render();
        this._notifyChange();
    }

    /**
     * Cancel current polygon drawing
     */
    cancelCurrentPolygon() {
        this.currentPoints = [];
        this._render();
        this._notifyChange();
    }

    /**
     * Undo last point
     */
    undoLastPoint() {
        if (this.currentPoints.length > 0) {
            this.currentPoints.pop();
            this._render();
            this._notifyChange();
        }
    }

    /**
     * Delete selected polygon
     */
    deleteSelected() {
        if (this.selectedIndex !== -1) {
            this.polygons.splice(this.selectedIndex, 1);
            this.selectedIndex = -1;
            if (this.onPolygonSelect) {
                this.onPolygonSelect(null, -1);
            }
            this._render();
            this._notifyChange();
        }
    }

    /**
     * Find polygon at given point
     */
    _findPolygonAtPoint(x, y) {
        for (let i = this.polygons.length - 1; i >= 0; i--) {
            if (this._isPointInPolygon(x, y, this.polygons[i].points)) {
                return i;
            }
        }
        return -1;
    }

    /**
     * Point-in-polygon test (ray casting)
     */
    _isPointInPolygon(x, y, points) {
        const canvasPoints = points.map(p => this.originalToCanvas(...p));

        let inside = false;
        for (let i = 0, j = canvasPoints.length - 1; i < canvasPoints.length; j = i++) {
            const [xi, yi] = canvasPoints[i];
            const [xj, yj] = canvasPoints[j];

            if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
                inside = !inside;
            }
        }
        return inside;
    }

    /**
     * Render everything
     */
    _render() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        if (this.backgroundImage) {
            this.ctx.drawImage(
                this.backgroundImage,
                0, 0,
                this.canvas.width,
                this.canvas.height
            );
        }

        this.polygons.forEach((polygon, index) => {
            this._drawPolygon(polygon.points, index);
        });

        if (this.currentPoints.length > 0) {
            this._drawCurrentPolygon();
        }
    }

    /**
     * Draw a completed polygon
     */
    _drawPolygon(points, index) {
        const ctx = this.ctx;
        const isSelected = index === this.selectedIndex;
        const isHovered = index === this.hoveredIndex && !isSelected;

        let color = this.options.colors.completed;
        if (isSelected) color = this.options.colors.selected;
        else if (isHovered) color = this.options.colors.hover;

        const canvasPoints = points.map(p => this.originalToCanvas(...p));

        ctx.beginPath();
        ctx.moveTo(...canvasPoints[0]);
        canvasPoints.slice(1).forEach(p => ctx.lineTo(...p));
        ctx.closePath();

        ctx.fillStyle = this._hexToRgba(color, this.options.fillAlpha);
        ctx.fill();

        ctx.strokeStyle = color;
        ctx.lineWidth = this.options.lineWidth;
        ctx.stroke();

        if (isSelected) {
            canvasPoints.forEach(([x, y]) => {
                ctx.beginPath();
                ctx.arc(x, y, this.options.pointRadius, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 2;
                ctx.stroke();
            });
        }

        if (canvasPoints.length > 0) {
            const polygon = this.polygons[index];
            const [labelX, labelY] = canvasPoints[0];
            ctx.fillStyle = '#fff';
            ctx.font = 'bold 12px Arial';
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 3;
            ctx.strokeText(polygon.name, labelX + 8, labelY - 8);
            ctx.fillText(polygon.name, labelX + 8, labelY - 8);
        }
    }

    /**
     * Draw polygon currently being created
     */
    _drawCurrentPolygon() {
        const ctx = this.ctx;
        const color = this.options.colors.drawing;

        if (this.currentPoints.length === 0) return;

        ctx.beginPath();
        ctx.moveTo(...this.currentPoints[0]);
        this.currentPoints.slice(1).forEach(p => ctx.lineTo(...p));

        ctx.strokeStyle = color;
        ctx.lineWidth = this.options.lineWidth;
        ctx.stroke();

        this.currentPoints.forEach(([x, y]) => {
            ctx.beginPath();
            ctx.arc(x, y, this.options.pointRadius, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
        });
    }

    /**
     * Draw preview line from last point to cursor
     */
    _drawPreviewLine(x, y) {
        if (this.currentPoints.length === 0) return;

        const ctx = this.ctx;
        const lastPoint = this.currentPoints[this.currentPoints.length - 1];

        ctx.beginPath();
        ctx.moveTo(...lastPoint);
        ctx.lineTo(x, y);
        ctx.strokeStyle = this.options.colors.drawing;
        ctx.lineWidth = 1;
        ctx.setLineDash([5, 5]);
        ctx.stroke();
        ctx.setLineDash([]);

        if (this.currentPoints.length >= 2) {
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(...this.currentPoints[0]);
            ctx.strokeStyle = this._hexToRgba(this.options.colors.drawing, 0.5);
            ctx.setLineDash([5, 5]);
            ctx.stroke();
            ctx.setLineDash([]);
        }
    }

    /**
     * Convert hex color to rgba
     */
    _hexToRgba(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    /**
     * Notify change callback
     */
    _notifyChange() {
        if (this.onChange) {
            this.onChange({
                polygons: this.polygons,
                currentPoints: this.currentPoints,
                hasUnsavedChanges: this.polygons.length > 0 || this.currentPoints.length > 0
            });
        }
    }

    /**
     * Get all polygons as coordinates (for saving)
     */
    getPolygonsForSave() {
        return this.polygons.map(p => ({
            name: p.name,
            coordinates: p.points
        }));
    }

    /**
     * Load existing polygons (for editing)
     */
    loadPolygons(polygons) {
        this.polygons = polygons.map(p => ({
            points: p.coordinates || p.points,
            name: p.name
        }));
        this.selectedIndex = -1;
        this._render();
    }

    /**
     * Update polygon name
     */
    updatePolygonName(index, name) {
        if (index >= 0 && index < this.polygons.length) {
            this.polygons[index].name = name;
            this._render();
        }
    }

    /**
     * Get polygon count
     */
    getPolygonCount() {
        return this.polygons.length;
    }

    /**
     * Check if currently drawing
     */
    isDrawing() {
        return this.currentPoints.length > 0;
    }

    /**
     * Reset all state
     */
    reset() {
        this.polygons = [];
        this.currentPoints = [];
        this.selectedIndex = -1;
        this.hoveredIndex = -1;
        this._render();
        this._notifyChange();
    }
}
