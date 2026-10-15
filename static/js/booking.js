/* Ngày trả >= ngày nhận NGAY KHI NHẬP, không chờ bấm Search. */
for(const form of document.querySelectorAll('[data-date-form]')){
    const nhan=form.querySelector('[name=check_in]'),tra=form.querySelector('[name=check_out]');
    const moc={ci:nhan.value,co:tra.value,type:form.querySelector('[name=room_type]')?.value};
    function suaNgay(){tra.min=nhan.value||nhan.min;if(tra.value&&tra.value<tra.min)tra.value=tra.min;
        if(!form.hasAttribute('data-counter-form')){
            const daDoi=nhan.value!==moc.ci||tra.value!==moc.co||form.querySelector('[name=room_type]')?.value!==moc.type;
            for(const nut of document.querySelectorAll('[data-book-result] button'))nut.disabled=daDoi;
            for(const link of document.querySelectorAll('[data-book-result] a')){link.setAttribute('aria-disabled',String(daDoi));link.tabIndex=daDoi?-1:0;}
            document.querySelector('[data-stale-notice]')?.classList.toggle('d-none',!daDoi);
        }
    }
    for(const link of document.querySelectorAll('[data-book-result] a'))link.addEventListener('click',e=>{if(link.getAttribute('aria-disabled')==='true')e.preventDefault();});
    for(const input of [nhan,tra]){input.addEventListener('input',suaNgay);input.addEventListener('change',suaNgay);}form.querySelector('[name=room_type]')?.addEventListener('change',suaNgay);suaNgay();
    if(!form.hasAttribute('data-counter-form'))continue;
    const phong=form.querySelector('[name=room_id]'),nut=document.getElementById('counter-submit'),bao=document.getElementById('availability-status');let lanTai=0;
    function tinhTien(){const dem=Math.max(1,(Date.parse(tra.value)-Date.parse(nhan.value))/86400000);const gia=Number(phong.selectedOptions[0]?.dataset.price||0);document.getElementById('price-preview').textContent=gia&&Number.isFinite(dem)?`${dem} đêm × AED ${gia.toFixed(2)} = AED ${(dem*gia).toFixed(2)}. Cọc tại quầy: 0.`:'Chọn phòng để tính tiền.';nut.disabled=!phong.value;}
    async function kiemTra(){const lan=++lanTai;suaNgay();nut.disabled=true;if(!nhan.validity.valid||!tra.validity.valid)return;bao.textContent='Đang kiểm tra phòng...';try{const r=await fetch(form.dataset.availability+'?'+new URLSearchParams({check_in:nhan.value,check_out:tra.value}));if(!r.ok||!r.headers.get('content-type')?.includes('application/json'))throw Error();const data=await r.json();if(lan!==lanTai)return;const cu=phong.value;phong.replaceChildren(new Option('Chọn phòng',''));for(const p of data.rooms){const o=new Option(`${p.number} · ${p.type} · AED ${p.price}`,p.id);o.dataset.price=p.price;phong.add(o);}phong.value=[...phong.options].some(o=>o.value===cu)?cu:'';bao.textContent=data.rooms.length+' phòng trống theo lịch (đã tính ngày dọn).';tinhTien();}catch{if(lan!==lanTai)return;phong.replaceChildren(new Option('Chưa kiểm tra được phòng',''));bao.textContent='Không tải được lịch. Hãy đổi ngày hoặc tải lại.';}}
    nhan.addEventListener('change',kiemTra);tra.addEventListener('change',kiemTra);phong.addEventListener('change',tinhTien);
    const khach=form.querySelector('[name=guest_id]'),ten=form.querySelector('[name=guest_name]');function chonKhach(){ten.required=!khach.value;}khach.addEventListener('change',chonKhach);chonKhach();kiemTra();
}
