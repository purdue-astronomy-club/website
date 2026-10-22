(() => {
 const input=document.querySelector('#photos'), output=document.querySelector('#prepared-photos');
 const urls=[];
 input.addEventListener('change',async()=>{
  urls.forEach(url=>URL.revokeObjectURL(url));urls.length=0;output.replaceChildren();
  for(const file of input.files){
   const row=document.createElement('p');row.textContent='Preparing '+file.name+'…';output.append(row);
   try{
    if(!['image/jpeg','image/png','image/webp'].includes(file.type))throw new Error('Choose a supported image');
    const bitmap=await createImageBitmap(file,{imageOrientation:'from-image'});
    const scale=Math.min(1,2000/Math.max(bitmap.width,bitmap.height));
    const canvas=document.createElement('canvas');canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);
    canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
    const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/webp',.87));
    if(!blob)throw new Error('Could not prepare image');
    const url=URL.createObjectURL(blob);urls.push(url);const a=document.createElement('a');
    a.href=url;a.download=file.name.replace(/\.[^.]+$/,'').replace(/[^a-zA-Z0-9-]/g,'-').toLowerCase()+'-web.webp';a.textContent='Download '+a.download+' ('+Math.round(blob.size/1024)+' KB)';
    row.replaceChildren(a);
   }catch(error){row.textContent=file.name+': '+error.message;}
  }
 });
})();
