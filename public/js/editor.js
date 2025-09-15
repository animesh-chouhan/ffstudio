import { initHistory } from './history.js';

const canvas = document.getElementById('editorCanvas');
const ctx = canvas.getContext('2d');

// Example: load blank bg
ctx.fillStyle = '#333';
ctx.fillRect(0, 0, canvas.width, canvas.height);

// Toolbar events
document.getElementById('cropBtn').addEventListener('click', () => {
    console.log('Crop tool activated');
});

document.getElementById('rotateBtn').addEventListener('click', () => {
    console.log('Rotate tool activated');
});

document.getElementById('resizeBtn').addEventListener('click', () => {
    console.log('Resize tool activated');
});

document.getElementById('flipBtn').addEventListener('click', () => {
    console.log('Flip tool activated');
});

// Undo / Redo
document.getElementById('undoBtn').addEventListener('click', () => {
    console.log('Undo');
});

document.getElementById('redoBtn').addEventListener('click', () => {
    console.log('Redo');
});

// Download
document.getElementById('downloadBtn').addEventListener('click', () => {
    const link = document.createElement('a');
    link.download = 'edited.png';
    link.href = canvas.toDataURL();
    link.click();
});

initHistory(canvas, ctx);
