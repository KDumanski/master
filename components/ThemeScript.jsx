export default function ThemeScript() {
  const js = `(function(){try{
    var t = localStorage.getItem('hub-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', t);
  }catch(e){ document.documentElement.setAttribute('data-theme','dark'); }
  document.documentElement.classList.add('js-ready');
  })();`;
  return <script dangerouslySetInnerHTML={{ __html: js }} />;
}
