(()=>{
 const config=window.CRAFTI_COMMUNITY||{};
 const enabled=!!(config.url&&config.anonKey);
 const root=document.getElementById('community');
 if(!root)return;
 if(!enabled){root.innerHTML='<p class="notice">La comunidad pública estará disponible cuando se conecte el servicio de comentarios. Las reacciones actuales siguen siendo privadas de cada dispositivo.</p>';return}
 if(!/^https:\/\/[a-z0-9-]+\.supabase\.co\/?$/i.test(config.url)){root.textContent='Configuración de comunidad inválida.';return}
 const api=config.url.replace(/\/$/,'')+'/rest/v1/';let token=null,userId=null,selected=null;
 const authStoreKey='crafti_auth_session_v2';
 function loadSession(){try{const v=JSON.parse(sessionStorage.getItem(authStoreKey)||'null');if(v&&v.expires_at>Date.now()+30000){token=v.access_token;userId=v.user_id;return true}}catch{}return false}
 function saveSession(data){try{sessionStorage.setItem(authStoreKey,JSON.stringify({access_token:data.access_token,user_id:data.user?.id,expires_at:Date.now()+(data.expires_in||3600)*1000}))}catch{}}
 function logout(){token=null;userId=null;try{sessionStorage.removeItem(authStoreKey)}catch{}status('Sesión cerrada.');if(selected)show(selected)}
 const el=(s)=>root.querySelector(s);
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 async function req(path,options={}){let res=await fetch(api+path,{...options,headers:{apikey:config.anonKey,Authorization:'Bearer '+(token||config.anonKey),'Content-Type':'application/json',...options.headers}});if(!res.ok)throw Error('Solicitud no completada ('+res.status+').');return res.status===204?null:res.json()}
 async function signIn(email){let r=await fetch(config.url+'/auth/v1/otp',{method:'POST',headers:{apikey:config.anonKey,'Content-Type':'application/json'},body:JSON.stringify({email,create_user:true})});if(!r.ok)throw Error('No se pudo enviar el acceso por correo.');}
 async function verify(email,code){let r=await fetch(config.url+'/auth/v1/verify',{method:'POST',headers:{apikey:config.anonKey,'Content-Type':'application/json'},body:JSON.stringify({email,token:code,type:'email'})});if(!r.ok)throw Error('Código incorrecto o caducado.');let d=await r.json();token=d.access_token;userId=d.user?.id;saveSession(d);}
 const base='<h2>Comunidad Crafti Gaming</h2><p class="meta">Los comentarios se revisan antes de aparecer públicamente. No compartas datos personales.</p><label>Correo para participar <input id="community-email" type="email" maxlength="254" placeholder="tu@correo.com"></label> <button id="send-code">Enviar código</button><label>Código recibido <input id="community-code" inputmode="numeric" maxlength="12" placeholder="Código"></label> <button id="verify-code">Ingresar</button><button id="community-logout" type="button">Cerrar sesión</button><p id="community-state" aria-live="polite"></p><div id="community-article"></div>';
 root.innerHTML=base;
 const hadSession=loadSession();
 el('#community-logout').onclick=logout;
 if(hadSession)el('#community-state').textContent='Sesión recuperada para esta pestaña.';
 function status(s){el('#community-state').textContent=s}
 el('#send-code').onclick=async()=>{try{let email=el('#community-email').value.trim();if(!/^\S+@\S+\.\S+$/.test(email))throw Error('Introduce un correo válido.');await signIn(email);status('Revisa tu correo para obtener el código.')}catch(e){status(e.message)}};
 el('#verify-code').onclick=async()=>{try{await verify(el('#community-email').value.trim(),el('#community-code').value.trim());status('Sesión iniciada.');if(selected)await show(selected)}catch(e){status(e.message)}};
 async function show(article){selected=article;let area=el('#community-article');area.innerHTML='<h3>Comentarios: '+esc(article.title)+'</h3><p>Cargando…</p>';
 try{
  let id=encodeURIComponent(article.id);
  let [comments,reactions]=await Promise.all([req('comments?article_id=eq.'+id+'&status=eq.approved&select=body,created_at&order=created_at.desc&limit=30'),req('reactions?article_id=eq.'+id+'&select=reaction')]);
  let likes=reactions.filter(x=>x.reaction==='like').length,wows=reactions.filter(x=>x.reaction==='wow').length;
  area.innerHTML='<h3>Comentarios: '+esc(article.title)+'</h3><p>👍 '+likes+' · 🔥 '+wows+'</p><button id="community-like">👍 Me gusta</button> <button id="community-wow">🔥 Sorprende</button><div class="community-comments">'+(comments.length?comments.map(c=>'<p class="community-comment">'+esc(c.body)+'<small> · '+esc(new Date(c.created_at).toLocaleDateString('es-PE'))+'</small></p>').join(''):'<p class="meta">Todavía no hay comentarios aprobados.</p>')+'</div><label for="comment-body">Escribe tu comentario</label><textarea id="comment-body" rows="3" maxlength="500" placeholder="Tu opinión (3–500 caracteres)"></textarea><button id="submit-comment">Enviar para revisión</button>';
  for(let reaction of ['like','wow'])el('#community-'+reaction).onclick=async()=>{if(!token)return status('Inicia sesión para reaccionar.');try{await req('reactions?on_conflict=article_id,user_id',{method:'POST',headers:{Prefer:'resolution=merge-duplicates'},body:JSON.stringify({article_id:article.id,user_id:userId,reaction})});await show(article)}catch(e){status(e.message)}};
  el('#submit-comment').onclick=async()=>{if(!token)return status('Inicia sesión para comentar.');let body=el('#comment-body').value.trim();if(body.length<3||body.length>500)return status('El comentario debe tener entre 3 y 500 caracteres.');try{await req('comments',{method:'POST',body:JSON.stringify({article_id:article.id,user_id:userId,body,status:'pending'})});el('#comment-body').value='';status('Comentario enviado. Aparecerá después de su revisión.')}catch(e){status(e.message)}};
 }catch(e){area.textContent='No se pudieron cargar los comentarios: '+e.message}
 }
 window.CraftiCommunity={show};
})();
