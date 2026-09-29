import fs from 'node:fs';
import {initializeTestEnvironment,assertFails,assertSucceeds} from '@firebase/rules-unit-testing';
import {doc,setDoc} from 'firebase/firestore';
const env=await initializeTestEnvironment({projectId:'demo-boomyard',firestore:{rules:fs.readFileSync((process.env.RULES_FILE||new URL('../firestore.rules',import.meta.url)),'utf8')},storage:{rules:fs.readFileSync((process.env.STORAGE_RULES_FILE||new URL('../storage.rules',import.meta.url)),'utf8')}});
try{
 await env.withSecurityRulesDisabled(async ctx=>{const db=ctx.firestore();await setDoc(doc(db,'users','staff'),{email:'staff@example.com',role:'employee'});await setDoc(doc(db,'users','client'),{email:'client@example.com',role:'client'});await setDoc(doc(db,'projects','p1'),{clientUid:'client'});await setDoc(doc(db,'projects','p2'),{clientUid:'other'})});
 const worker=env.authenticatedContext('staff',{email:'staff@example.com',email_verified:true}).storage();
 const client=env.authenticatedContext('client',{email:'client@example.com',email_verified:true}).storage();
 const pic=worker.ref('projects/p1/photo.png');await assertSucceeds(pic.put(new Uint8Array([1,2,3]),{contentType:'image/png'}));
 await assertSucceeds(worker.ref('projects/p2/photo.png').put(new Uint8Array([1,2,3]),{contentType:'image/png'}));
 await assertSucceeds(client.ref('projects/p1/photo.png').getDownloadURL());
 await assertSucceeds(client.ref('projects/p1/reference.png').put(new Uint8Array([1]),{contentType:'image/png'}));
 await assertFails(client.ref('projects/p1/drawing.pdf').put(new Uint8Array([1]),{contentType:'application/pdf'}));
 await assertFails(client.ref('projects/p2/photo.png').getDownloadURL());
 await assertSucceeds(client.ref('avatars/client/me.png').put(new Uint8Array([1]),{contentType:'image/png'}));
 await assertFails(client.ref('avatars/staff/me.png').put(new Uint8Array([1]),{contentType:'image/png'}));
 console.log('Storage rules tests passed');
}finally{await env.cleanup()}
