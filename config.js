// config.js — 채팅 UI가 사용하는 공개 설정 (브라우저에 노출됨)
// ⚠️ service_role/secret 키는 절대 여기에 넣지 마세요. publishable(anon) key만 사용.
window.SUPABASE_CONFIG = {
  url: 'https://gfpsahhfllozfqczyoza.supabase.co',
  anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdmcHNhaGhmbGxvemZxY3p5b3phIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY1MjM4MTcsImV4cCI6MjEwMjA5OTgxN30.Wha6rimow-cDWO3ek2hMWrSBoonp7Tl7FDgFRVoymC0',
  defaultModel: 'MiniMax-M3',
  // 다온에이전트 시스템(DAON /api/models) 등록 프로바이더 모델 목록 (PC 커넥터 연동 시 실시간 동기화됨)
  modelGroups: [
    {
        "provider": "Omniroute",
        "provider_key": "omniroute",
        "models": [
            {
                "id": "auto",
                "label": "auto (free multi-provider routing)",
                "type": "chat"
            },
            {
                "id": "auto/coding",
                "label": "auto/coding (coding-focused routing)",
                "type": "chat"
            },
            {
                "id": "groq/openai/gpt-oss-120b",
                "label": "GPT-OSS 120B (Groq · free)",
                "type": "chat"
            },
            {
                "id": "groq/qwen/qwen3.8-27b",
                "label": "Qwen3.8 27B (Groq · free)",
                "type": "chat"
            },
            {
                "id": "groq/groq/compound",
                "label": "Compound (Groq · free)",
                "type": "chat"
            },
            {
                "id": "nvidia/deepseek-ai/deepseek-v4-pro-0813",
                "label": "DeepSeek V4 Pro (NVIDIA NIM · free)",
                "type": "chat"
            },
            {
                "id": "nvidia/deepseek-ai/deepseek-v4-flash-0731",
                "label": "DeepSeek V4 Flash (NVIDIA NIM · free)",
                "type": "chat"
            }
        ]
    },
    {
        "provider": "MiniMax",
        "provider_key": "minimax",
        "models": [
            {
                "id": "MiniMax-M3",
                "label": "MiniMax-M3",
                "type": "chat"
            },
            {
                "id": "MiniMax-M2.7",
                "label": "MiniMax-M2.7",
                "type": "chat"
            },
            {
                "id": "image-01",
                "label": "image-01",
                "type": "image"
            }
        ]
    },
    {
        "provider": "DeepSeek",
        "provider_key": "deepseek",
        "models": [
            {
                "id": "deepseek-v4-flash",
                "label": "deepseek-v4-flash",
                "type": "chat"
            },
            {
                "id": "deepseek-v4-pro",
                "label": "deepseek-v4-pro",
                "type": "chat"
            }
        ]
    },
    {
        "provider": "Alibaba Cloud (Token Plan)",
        "provider_key": "qwen-token-plan",
        "models": [
            {
                "id": "deepseek-v4-pro",
                "label": "deepseek-v4-pro",
                "type": "chat"
            },
            {
                "id": "wan2.7-image",
                "label": "wan2.7-image",
                "type": "image"
            },
            {
                "id": "wan2.7-image-pro",
                "label": "wan2.7-image-pro",
                "type": "image"
            },
            {
                "id": "deepseek-v4-flash-0731",
                "label": "deepseek-v4-flash-0731",
                "type": "chat"
            },
            {
                "id": "qwen3.8-max",
                "label": "qwen3.8-max",
                "type": "chat"
            },
            {
                "id": "qwen3.8-flash",
                "label": "qwen3.8-flash",
                "type": "chat"
            }
        ]
    },
    {
        "provider": "OpenCode Go",
        "provider_key": "opencode-go",
        "models": [
            {
                "id": "longcat-2.0",
                "label": "longcat-2.0",
                "type": "chat"
            },
            {
                "id": "glm-5.3-flash",
                "label": "glm-5.3-flash",
                "type": "chat"
            },
            {
                "id": "deepseek-v4-flash-vision-exp",
                "label": "deepseek-v4-flash-vision-exp",
                "type": "chat"
            },
            {
                "id": "muse-spark-1.3-contributor",
                "label": "muse-spark-1.3-contributor",
                "type": "chat"
            }
        ]
    },
    {
        "provider": "OpenRouter",
        "provider_key": "openrouter",
        "models": [
            {
                "id": "z-ai/glm-5.3-flash",
                "label": "z-ai/glm-5.3-flash",
                "type": "chat"
            },
            {
                "id": "bytedance/seedance-2.0-mini",
                "label": "bytedance/seedance-2.0-mini",
                "type": "video"
            },
            {
                "id": "alibaba/wan-3.0",
                "label": "alibaba/wan-3.0",
                "type": "video"
            }
        ]
    }
],
  models: [
    {
        "provider": "Omniroute",
        "id": "auto",
        "label": "auto (free multi-provider routing)",
        "type": "chat"
    },
    {
        "provider": "Omniroute",
        "id": "auto/coding",
        "label": "auto/coding (coding-focused routing)",
        "type": "chat"
    },
    {
        "provider": "Omniroute",
        "id": "groq/openai/gpt-oss-120b",
        "label": "GPT-OSS 120B (Groq · free)",
        "type": "chat"
    },
    {
        "provider": "Omniroute",
        "id": "groq/qwen/qwen3.8-27b",
        "label": "Qwen3.8 27B (Groq · free)",
        "type": "chat"
    },
    {
        "provider": "Omniroute",
        "id": "groq/groq/compound",
        "label": "Compound (Groq · free)",
        "type": "chat"
    },
    {
        "provider": "Omniroute",
        "id": "nvidia/deepseek-ai/deepseek-v4-pro-0813",
        "label": "DeepSeek V4 Pro (NVIDIA NIM · free)",
        "type": "chat"
    },
    {
        "provider": "Omniroute",
        "id": "nvidia/deepseek-ai/deepseek-v4-flash-0731",
        "label": "DeepSeek V4 Flash (NVIDIA NIM · free)",
        "type": "chat"
    },
    {
        "provider": "MiniMax",
        "id": "MiniMax-M3",
        "label": "MiniMax-M3",
        "type": "chat"
    },
    {
        "provider": "MiniMax",
        "id": "MiniMax-M2.7",
        "label": "MiniMax-M2.7",
        "type": "chat"
    },
    {
        "provider": "MiniMax",
        "id": "image-01",
        "label": "image-01",
        "type": "image"
    },
    {
        "provider": "DeepSeek",
        "id": "deepseek-v4-flash",
        "label": "deepseek-v4-flash",
        "type": "chat"
    },
    {
        "provider": "DeepSeek",
        "id": "deepseek-v4-pro",
        "label": "deepseek-v4-pro",
        "type": "chat"
    },
    {
        "provider": "Alibaba Cloud (Token Plan)",
        "id": "deepseek-v4-pro",
        "label": "deepseek-v4-pro",
        "type": "chat"
    },
    {
        "provider": "Alibaba Cloud (Token Plan)",
        "id": "wan2.7-image",
        "label": "wan2.7-image",
        "type": "image"
    },
    {
        "provider": "Alibaba Cloud (Token Plan)",
        "id": "wan2.7-image-pro",
        "label": "wan2.7-image-pro",
        "type": "image"
    },
    {
        "provider": "Alibaba Cloud (Token Plan)",
        "id": "deepseek-v4-flash-0731",
        "label": "deepseek-v4-flash-0731",
        "type": "chat"
    },
    {
        "provider": "Alibaba Cloud (Token Plan)",
        "id": "qwen3.8-max",
        "label": "qwen3.8-max",
        "type": "chat"
    },
    {
        "provider": "Alibaba Cloud (Token Plan)",
        "id": "qwen3.8-flash",
        "label": "qwen3.8-flash",
        "type": "chat"
    },
    {
        "provider": "OpenCode Go",
        "id": "longcat-2.0",
        "label": "longcat-2.0",
        "type": "chat"
    },
    {
        "provider": "OpenCode Go",
        "id": "glm-5.3-flash",
        "label": "glm-5.3-flash",
        "type": "chat"
    },
    {
        "provider": "OpenCode Go",
        "id": "deepseek-v4-flash-vision-exp",
        "label": "deepseek-v4-flash-vision-exp",
        "type": "chat"
    },
    {
        "provider": "OpenCode Go",
        "id": "muse-spark-1.3-contributor",
        "label": "muse-spark-1.3-contributor",
        "type": "chat"
    },
    {
        "provider": "OpenRouter",
        "id": "z-ai/glm-5.3-flash",
        "label": "z-ai/glm-5.3-flash",
        "type": "chat"
    },
    {
        "provider": "OpenRouter",
        "id": "bytedance/seedance-2.0-mini",
        "label": "bytedance/seedance-2.0-mini",
        "type": "video"
    },
    {
        "provider": "OpenRouter",
        "id": "alibaba/wan-3.0",
        "label": "alibaba/wan-3.0",
        "type": "video"
    }
]
};
