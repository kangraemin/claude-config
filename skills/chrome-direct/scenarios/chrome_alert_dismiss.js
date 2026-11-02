var se=Application("System Events"),p=se.processes["Google Chrome"];
var ws=p.windows.whose({name:{_contains:"내용:"}});var n=ws.length;var r="none";
if(n>0){var w=ws[0],btn=null;function walk(e,d){if(d>7||btn)return;var kids=e.uiElements();for(var i=0;i<kids.length;i++){var k=kids[i],x="";try{x=k.role()}catch(_){};if(x=="AXButton"){btn=k;return};walk(k,d+1)}}walk(w,0);if(btn){btn.click();r="clicked"}}
r
