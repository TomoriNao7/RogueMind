// RogueMind preload — 安全隔离，不暴露 Node.js API 给渲染进程
const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('rogueMind', {
  platform: process.platform,
  version: '0.1.0',
});
