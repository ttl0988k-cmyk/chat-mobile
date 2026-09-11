// app.models.js - model select/stream sync
(function (APP) {
'use strict';

  APP.renderModelOptions = function renderModelOptions(groupsOrModels) {
    const sel = APP.$('model-select');
    if (!sel) return;
    const prevVal = sel.value || APP.selectedModel || localStorage.getItem('daon_selected_model') || '';
    sel.innerHTML = '<option value="">기본 모델</option>';

    if (!groupsOrModels || groupsOrModels.length === 0) return;

    // 그룹 형식인지 평탄화된 형식인지 판별
    const isGroups = groupsOrModels[0] && Array.isArray(groupsOrModels[0].models);

    if (isGroups) {
      for (const g of groupsOrModels) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = g.provider || '기타';
        for (const m of (g.models || [])) {
          const opt = document.createElement('option');
          opt.value = m.id;
          opt.textContent = m.label || m.id;
          if (m.type && m.type !== 'chat') {
            opt.setAttribute('data-type', m.type);
          }
          optgroup.appendChild(opt);
        }
        if (optgroup.children.length > 0) {
          sel.appendChild(optgroup);
        }
      }
    } else {
      let lastProvider = '';
      let currentGroup = null;
      for (const m of groupsOrModels) {
        const p = m.provider || '기타';
        if (p !== lastProvider || !currentGroup) {
          currentGroup = document.createElement('optgroup');
          currentGroup.label = p;
          sel.appendChild(currentGroup);
          lastProvider = p;
        }
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.label || m.id;
        if (m.type && m.type !== 'chat') {
          opt.setAttribute('data-type', m.type);
        }
        currentGroup.appendChild(opt);
      }
    }

    // 선택 상태 복원
    if (prevVal && Array.from(sel.options).some(o => o.value === prevVal)) {
      sel.value = prevVal;
      APP.selectedModel = prevVal;
    } else {
      sel.value = '';
      APP.selectedModel = '';
    }
  };
  APP.loadModelList = async function loadModelList() {
    try {
      // 1단계: config.js 또는 localStorage 캐시로 즉각 렌더링 (지연/깜빡임 방지)
      let initialData = null;
      try {
        const cached = localStorage.getItem('daon_cached_models');
        if (cached) {
          const parsed = JSON.parse(cached);
          initialData = parsed.groups || parsed.models || parsed;
        }
      } catch (_) {}

      if (!initialData && window.SUPABASE_CONFIG) {
        initialData = window.SUPABASE_CONFIG.modelGroups || window.SUPABASE_CONFIG.models || [];
      }

      if (initialData) {
        APP.renderModelOptions(initialData);
      }

      // 2단계: 로그인 사용자 대상 Supabase agent_memory 에서 실시간 동기화된 최신 모델 목록 가져오기
      if (APP.currentUserId) {
        const { data, error } = await APP.sb
          .from('agent_memory')
          .select('content, metadata, updated_at')
          .eq('user_id', APP.currentUserId)
          .eq('key', 'available_models')
          .order('updated_at', { ascending: false })
          .limit(1);

        if (!error && data && data.length > 0 && data[0].content) {
          try {
            const parsed = JSON.parse(data[0].content);
            const liveGroups = parsed.groups || parsed.models;
            if (liveGroups && liveGroups.length > 0) {
              APP.renderModelOptions(liveGroups);
              localStorage.setItem('daon_cached_models', data[0].content);
            }
          } catch (parseErr) {
            console.warn('[APP.loadModelList] Supabase 모델 파싱 실패:', parseErr);
          }
        }

        // 3단계: Supabase Realtime 실시간 변경 감지 구독 (최초 1회)
        APP.subscribeModelSync();
      }
    } catch (e) {
      console.error('모델 목록 로드 실패:', e);
    }
  };
  APP.subscribeModelSync = function subscribeModelSync() {
    if (APP._modelSyncSubscribed || !APP.currentUserId) return;
    APP._modelSyncSubscribed = true;
    try {
      APP.sb.channel('realtime-available-models')
        .on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'agent_memory',
            filter: `user_id=eq.${APP.currentUserId}`
          },
          (payload) => {
            const rec = payload.new || {};
            if (rec.key === 'available_models' && rec.content) {
              try {
                const parsed = JSON.parse(rec.content);
                const liveGroups = parsed.groups || parsed.models;
                if (liveGroups && liveGroups.length > 0) {
                  APP.renderModelOptions(liveGroups);
                  localStorage.setItem('daon_cached_models', rec.content);
                  console.log('🔄 [Realtime] DAON 프로바이더 모델 실시간 동기화 완료');
                }
              } catch (_) {}
            }
          }
        )
        .subscribe();
    } catch (e) {
      console.warn('[APP.subscribeModelSync] Realtime 구독 실패:', e);
    }
  };
  APP.onModelChange = function onModelChange() {

    APP.selectedModel = APP.$('model-select').value;

    try { localStorage.setItem('daon_selected_model', APP.selectedModel); } catch (_) {}

  };
})(window.DAON_APP);

