/* 文档创建时仅接收原生主题枚举，在任何主题样式加载前应用。 */
(() => {
  const theme = window.pdmEditorInitialTheme === 'LIGHT' ? 'LIGHT' : 'DARK';
  delete window.pdmEditorInitialTheme;
  document.documentElement.dataset.pdmEditorTheme = theme;
  document.documentElement.classList.toggle('light', theme === 'LIGHT');
})();
