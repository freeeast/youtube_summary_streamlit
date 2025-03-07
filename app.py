import streamlit as st
import re
import os
from youtube_transcript_api import YouTubeTranscriptApi
import requests
import json
import llm 

# 设置页面配置
st.set_page_config(
    page_title="YouTube 视频摘要", 
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None,
    page_icon="🎬"
)

# 设置深色主题
st.markdown("""
<style>
    .main {
        background-color: #111827;
        color: white;
    }
    .stButton>button {
        background-color: #171F2B;
        color: white;
        border: 1px solid #374151;
        border-radius: 4px;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover {
        border-color: #6366F1;
        color: #6366F1;
    }
    .stTextInput>div>div>input {
        background-color: #1F2937;
        color: white;
        border: 1px solid #374151;
    }
    .stSelectbox>div>div>div {
        background-color: #1F2937;
        color: white;
        border: 1px solid #374151;
    }
    h1, h2, h3 {
        color: white;
    }
    .stExpander {
        background-color: #1F2937;
        border: 1px solid #374151;
    }
    .summary-container {
        background-color: #1F2937;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #374151;
    }
    a {
        color: #60A5FA;
    }
    .stSpinner > div > div {
        border-top-color: #6366F1 !important;
    }
    .success-message {
        background-color: rgba(16, 185, 129, 0.2);
        border-radius: 4px;
        padding: 8px 12px;
        border-left: 4px solid #10B981;
    }
    .warning-message {
        background-color: rgba(245, 158, 11, 0.2);
        border-radius: 4px;
        padding: 8px 12px;
        border-left: 4px solid #F59E0B;
    }
    .error-message {
        background-color: rgba(239, 68, 68, 0.2);
        border-radius: 4px;
        padding: 8px 12px;
        border-left: 4px solid #EF4444;
    }
</style>
""", unsafe_allow_html=True)

# 自定义消息函数
def custom_success(text):
    st.markdown(f'<div class="success-message">{text}</div>', unsafe_allow_html=True)

def custom_warning(text):
    st.markdown(f'<div class="warning-message">{text}</div>', unsafe_allow_html=True)

def custom_error(text):
    st.markdown(f'<div class="error-message">{text}</div>', unsafe_allow_html=True)

# 侧边栏设置
with st.sidebar:
    st.title("设置")
    show_debug = st.checkbox("显示调试信息", value=False)
    api_provider = st.radio("API提供商", ["OpenRouter", "GitHub"], index=0)
    
    if api_provider == "OpenRouter":
        model_options = {
            "anthropic/claude-3-haiku": "Claude 3 Haiku (快速)",
            "anthropic/claude-3-sonnet": "Claude 3 Sonnet (平衡)",
            "anthropic/claude-3-opus": "Claude 3 Opus (高质量)"
        }
    else:
        model_options = {
            "gpt-4o-mini": "GPT-4o Mini (快速)",
            "gpt-4o": "GPT-4o (高质量)"
        }
    
    selected_model = st.selectbox(
        "选择模型", 
        options=list(model_options.keys()), 
        format_func=lambda x: model_options[x],
        index=0
    )
    
    if show_debug:
        st.write("### 调试信息")
        st.write(f"当前工作目录: {os.getcwd()}")
        st.write(f"credentials文件存在: {os.path.exists('credentials')}")
        st.write(f".streamlit文件夹存在: {os.path.exists('.streamlit')}")
        if os.path.exists('.streamlit'):
            st.write(f".streamlit/secrets.toml存在: {os.path.exists('.streamlit/secrets.toml')}")

def extract_video_id(url):
    """从各种格式的 YouTube URL 中提取视频 ID"""
    if not url:
        return None
    
    # YouTube URL 的正则表达式模式
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_transcript_with_proxy(video_id, language_code='en'):
    """使用代理API获取字幕"""
    try:
        proxy_url = f"https://yt.vl.comp.polyu.edu.hk/transcript?language_code={language_code}&password=for_demo&video_id={video_id}"
        
        if show_debug:
            st.sidebar.info(f"正在使用代理API: {proxy_url}")
        
        response = requests.get(proxy_url, timeout=15)
        
        if response.status_code == 200:
            try:
                # 尝试解析JSON
                data = response.json()
                
                if show_debug:
                    st.sidebar.success("代理API返回数据成功")
                    st.sidebar.write(f"数据类型: {type(data)}")
                    if isinstance(data, dict):
                        st.sidebar.write(f"字典键: {list(data.keys())}")
                    elif isinstance(data, list) and len(data) > 0:
                        st.sidebar.write(f"列表第一项类型: {type(data[0])}")
                        if isinstance(data[0], dict):
                            st.sidebar.write(f"第一项键: {list(data[0].keys())}")
                
                # 处理不同的返回格式
                if isinstance(data, list):
                    # 列表格式，直接提取文本
                    texts = []
                    for item in data:
                        if isinstance(item, dict) and "text" in item:
                            texts.append(item["text"])
                    
                    if texts:
                        return " ".join(texts)
                elif isinstance(data, dict):
                    # 字典格式，可能有不同的结构
                    if "transcript" in data and isinstance(data["transcript"], list):
                        # 如果有transcript字段且是列表
                        texts = []
                        for item in data["transcript"]:
                            if isinstance(item, dict) and "text" in item:
                                texts.append(item["text"])
                        
                        if texts:
                            return " ".join(texts)
                    elif "text" in data:
                        # 直接有text字段
                        return data["text"]
                    else:
                        # 尝试迭代字典，看是否有字幕数据
                        texts = []
                        for key, value in data.items():
                            if isinstance(value, dict) and "text" in value:
                                texts.append(value["text"])
                        
                        if texts:
                            return " ".join(texts)
                
                # 如果无法解析结构，返回原始内容
                if show_debug:
                    st.sidebar.warning("无法解析数据结构，返回原始内容")
                return str(data)
            except Exception as json_e:
                if show_debug:
                    st.sidebar.error(f"JSON解析错误: {str(json_e)}")
                # 返回原始响应文本
                return response.text
        else:
            if show_debug:
                st.sidebar.error(f"代理API HTTP错误: {response.status_code}")
            return None
    except Exception as e:
        if show_debug:
            st.sidebar.error(f"代理API请求异常: {str(e)}")
        return None

def get_transcript(video_id, language='en'):
    """获取指定 YouTube 视频的字幕，带有自动故障转移到代理API"""
    # 转换语言代码为YouTube API可接受的格式
    language_code = language
    if language == 'zh-CN':
        language_code = 'zh-Hans'
    elif language == 'zh-TW':
        language_code = 'zh-Hant'
    
    if show_debug:
        st.sidebar.info(f"请求语言: {language}, 转换为: {language_code}")
    
    try:
        # 尝试直接获取字幕
        if show_debug:
            st.sidebar.info(f"尝试直接使用YouTube API获取字幕")
        
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language_code])
        
        if show_debug:
            st.sidebar.success("成功直接获取字幕")
        
        return " ".join([t["text"] for t in transcript])
    except Exception as e:
        custom_warning(f"直接获取字幕失败: {str(e)}")
        
        # 尝试使用代理API
        custom_info = st.empty()
        custom_info.markdown(f'<div class="info-message">正在尝试使用代理API获取字幕...</div>', unsafe_allow_html=True)
        
        transcript_text = get_transcript_with_proxy(video_id, language_code)
        
        if transcript_text:
            custom_info.empty()
            custom_success("成功通过代理API获取字幕")
            return transcript_text
        
        # 如果特定语言失败，尝试英文
        if language_code != 'en':
            custom_info.markdown(f'<div class="info-message">尝试获取英文字幕...</div>', unsafe_allow_html=True)
            
            # 先尝试直接获取英文
            try:
                en_transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                custom_info.empty()
                custom_success("成功获取英文字幕")
                custom_warning(f"未能获取{language}字幕，将使用英文字幕")
                return " ".join([t["text"] for t in en_transcript])
            except:
                # 再尝试通过代理获取英文
                en_transcript_text = get_transcript_with_proxy(video_id, 'en')
                
                if en_transcript_text:
                    custom_info.empty()
                    custom_success("成功通过代理API获取英文字幕")
                    custom_warning(f"未能获取{language}字幕，将使用英文字幕")
                    return en_transcript_text
        
        custom_info.empty()
        custom_error("无法获取任何语言的字幕")
        return None

def get_api_credentials():
    """获取API凭证"""
    # 使用侧边栏选择的API提供商和模型
    api_source = api_provider.lower()
    model_name = selected_model
    
    api_key = None
    api_endpoint = None
    
    # 方法1: 尝试从credentials文件读取
    try:
        if os.path.exists("credentials"):
            if show_debug:
                st.sidebar.success("找到credentials文件，尝试读取...")
                
            # 读取credentials文件
            current_section = None
            github_creds = {}
            openrouter_creds = {}
            
            with open("credentials", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("[OPENROUTER]"):
                        current_section = "openrouter"
                    elif line.startswith("[GITHUB]"):
                        current_section = "github"
                    elif "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        if current_section == "github":
                            github_creds[key] = value
                        elif current_section == "openrouter":
                            openrouter_creds[key] = value
            
            # 根据选择的API提供商设置凭证
            if api_source == "github" and github_creds and "GITHUB_API_KEY" in github_creds:
                if show_debug:
                    st.sidebar.success("从credentials文件加载GitHub API凭证")
                api_key = github_creds["GITHUB_API_KEY"]
                api_endpoint = github_creds.get("GITHUB_API_ENDPOINT", "https://api.github.com/v1/chat/completions")
            elif api_source == "openrouter" and openrouter_creds and "OPENROUTER_API_KEY" in openrouter_creds:
                if show_debug:
                    st.sidebar.success("从credentials文件加载OpenRouter API凭证")
                api_key = openrouter_creds["OPENROUTER_API_KEY"]
                api_endpoint = openrouter_creds.get("OPENROUTER_API_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions")
    except Exception as e:
        if show_debug:
            st.sidebar.error(f"读取credentials文件时出错: {str(e)}")
    
    # 方法2: 尝试从Streamlit Secrets读取
    if api_key is None:
        try:
            if hasattr(st, "secrets"):
                if show_debug:
                    st.sidebar.info("尝试从Streamlit secrets读取...")
                
                if api_source == "github" and "GITHUB_API_KEY" in st.secrets:
                    if show_debug:
                        st.sidebar.success("从Streamlit secrets加载GitHub API凭证")
                    api_key = st.secrets["GITHUB_API_KEY"]
                    api_endpoint = st.secrets.get("GITHUB_API_ENDPOINT", "https://api.github.com/v1/chat/completions")
                elif api_source == "openrouter" and "OPENROUTER_API_KEY" in st.secrets:
                    if show_debug:
                        st.sidebar.success("从Streamlit secrets加载OpenRouter API凭证")
                    api_key = st.secrets["OPENROUTER_API_KEY"]
                    api_endpoint = st.secrets.get("OPENROUTER_API_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions")
        except Exception as e:
            if show_debug:
                st.sidebar.error(f"读取Streamlit secrets时出错: {str(e)}")
    
    # 方法3: 尝试从环境变量读取
    if api_key is None:
        if show_debug:
            st.sidebar.info("尝试从环境变量读取...")
        if api_source == "github" and os.environ.get("GITHUB_API_KEY"):
            if show_debug:
                st.sidebar.success("从环境变量加载GitHub API凭证")
            api_key = os.environ.get("GITHUB_API_KEY")
            api_endpoint = os.environ.get("GITHUB_API_ENDPOINT", "https://api.github.com/v1/chat/completions")
        elif api_source == "openrouter" and os.environ.get("OPENROUTER_API_KEY"):
            if show_debug:
                st.sidebar.success("从环境变量加载OpenRouter API凭证")
            api_key = os.environ.get("OPENROUTER_API_KEY")
            api_endpoint = os.environ.get("OPENROUTER_API_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions")
    
    # 方法4: 使用硬编码的API凭证作为备选
    if api_key is None:
        if show_debug:
            st.sidebar.warning("从上述方法未找到API凭证，使用硬编码的备选凭证")
        
        if api_source == "github":
            api_key = "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"
            api_endpoint = "https://api.github.com/v1/chat/completions"
        else:  # openrouter
            api_key = "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"
            api_endpoint = "https://openrouter.ai/api/v1/chat/completions"
    
    # 显示使用的API信息
    if api_key and show_debug:
        st.sidebar.success(f"成功配置API: {api_source}")
        st.sidebar.info(f"使用模型: {model_name}")
        st.sidebar.info(f"API端点: {api_endpoint}")
    
    return api_key, api_endpoint, model_name, api_source

def generate_summary(transcript, language, api_key, api_endpoint, model_name, api_source, detailed=False):
    """使用 LLM API 生成摘要"""
    if not transcript:
        return None, None
    
    # 限制文本长度，防止超过模型的最大输入限制
    max_length = 12000 if api_source == "openrouter" else 8000
    if len(transcript) > max_length:
        transcript_truncated = transcript[:max_length] + "... [内容过长，已截断]"
    else:
        transcript_truncated = transcript
    
    summary_type = "详细摘要" if detailed else "摘要"
    
    system_prompt = f"你是一个帮助用户总结 YouTube 视频内容的助手，提供清晰简洁的摘要。"
    user_prompt = f"请为这个 YouTube 视频字幕提供一个{summary_type}，使用{language}语言。重点关注主要内容和关键信息：{transcript_truncated}"
    
    # 根据来源（GitHub 或 OpenRouter）准备 API 请求
    headers = {
        "Content-Type": "application/json",
    }
    
    if api_source == "github":
        headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
    else:  # OpenRouter
        headers["Authorization"] = f"Bearer {api_key}"
        headers["HTTP-Referer"] = "https://streamlit.io/"  # OpenRouter 需要
        headers["X-Title"] = "YouTube Video Summarizer"  # 使用纯ASCII标题
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
    
    try:
        with st.spinner("正在生成摘要，请稍候..."):
            # 记录请求信息用于调试
            if show_debug:
                st.sidebar.write(f"API请求URL: {api_endpoint}")
                st.sidebar.write("请求Headers: " + str({k: v for k, v in headers.items() if k != "Authorization"}))
                st.sidebar.write(f"使用模型: {model_name}")
                
            # 使用json.dumps确保正确处理Unicode字符
            json_payload = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            
            # 使用原始bytes发送请求
            response = requests.post(
                api_endpoint, 
                headers=headers, 
                data=json_payload,
                timeout=60
            )
            
            # 记录API响应状态和内容前100个字符用于调试
            if show_debug:
                st.sidebar.write(f"API响应状态码: {response.status_code}")
                try:
                    response_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                    st.sidebar.write(f"API响应内容: {response_text}")
                except:
                    st.sidebar.write("无法显示响应内容")
            
            response.raise_for_status()
            response_data = response.json()
            
            # 根据 API 响应结构提取内容
            if api_source == "github":
                summary = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:  # OpenRouter
                summary = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return summary, user_prompt
    except Exception as e:
        custom_error(f"生成摘要时出错: {str(e)}")
        # 添加更详细的错误信息
        if hasattr(e, 'response') and e.response is not None:
            if show_debug:
                try:
                    st.sidebar.error(f"API错误详情: {e.response.text if hasattr(e.response, 'text') else '无详情'}")
                except:
                    st.sidebar.error("无法显示错误详情")
                    
        # 尝试使用备用API
        if api_source == "github":
            st.warning("GitHub API失败，尝试使用OpenRouter API...")
            try:
                # 切换到OpenRouter
                alt_api_key = "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"
                alt_api_endpoint = "https://openrouter.ai/api/v1/chat/completions"
                alt_model_name = "anthropic/claude-3-haiku"
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {alt_api_key}",
                    "HTTP-Referer": "https://streamlit.io/",
                    "X-Title": "YouTube Video Summarizer"
                }
                
                payload = {
                    "model": alt_model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                }
                
                json_payload = json.dumps(payload, ensure_ascii=False).encode('utf-8')
                
                with st.spinner("使用备用API重试..."):
                    response = requests.post(
                        alt_api_endpoint, 
                        headers=headers, 
                        data=json_payload,
                        timeout=60
                    )
                    
                    response.raise_for_status()
                    response_data = response.json()
                    summary = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    st.success("成功使用备用API生成摘要")
                    return summary, user_prompt
            except Exception as backup_e:
                if show_debug:
                    st.sidebar.error(f"备用API也失败: {str(backup_e)}")
                return None, user_prompt
        return None, user_prompt

def main():
    st.title("YouTube 视频摘要生成器")
    
    # 获取 API 凭证
    with st.spinner("正在初始化..."):
        api_key, api_endpoint, model_name, api_source = get_api_credentials()
    
    if not api_key or not api_endpoint or not model_name:
        st.error("未找到 API 凭证。请设置所需的环境变量或密钥。")
        st.info("您可以通过以下方式设置API凭证:")
        st.info("1. 创建包含API密钥的credentials文件")
        st.info("2. 在.streamlit/secrets.toml文件中设置API密钥")
        st.info("3. 设置环境变量")
        return
    
    # 创建两列布局：左侧为输入，右侧为结果
    left_col, right_col = st.columns([1, 2])
    
    with left_col:
        st.subheader("输入")
        # YouTube URL 输入
        youtube_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
        
        # 语言选择
        languages = {
            "en": "英语",
            "zh-TW": "繁体中文",
            "zh-CN": "简体中文",
            "es": "西班牙语",
            "fr": "法语",
            "de": "德语",
            "ja": "日语",
            "ko": "韩语"
        }
        
        selected_language = st.selectbox(
            "选择语言",
            options=list(languages.keys()),
            format_func=lambda x: languages[x],
            index=2 if "zh-CN" in languages else 0
        )
        
        # 初始化会话状态以存储摘要
        if "summary" not in st.session_state:
            st.session_state.summary = None
        if "detailed_summary" not in st.session_state:
            st.session_state.detailed_summary = None
        if "user_prompt" not in st.session_state:
            st.session_state.user_prompt = None
        if "detailed_user_prompt" not in st.session_state:
            st.session_state.detailed_user_prompt = None
        if "video_id" not in st.session_state:
            st.session_state.video_id = None
        if "transcript" not in st.session_state:
            st.session_state.transcript = None
        
        # 生成摘要按钮
        col1, col2 = st.columns(2)
        with col1:
            generate_summary_btn = st.button("生成简要摘要", use_container_width=True)
        with col2:
            generate_detailed_btn = st.button("生成详细摘要", use_container_width=True)
        
        # 显示当前使用的API和模型信息
        st.markdown("---")
        st.write(f"当前使用: **{api_source.capitalize()}** API")
        st.write(f"模型: **{model_name}**")
        st.info("可在侧边栏更改API和模型设置")
        
        if generate_summary_btn or generate_detailed_btn:
            is_detailed = generate_detailed_btn
            video_id = extract_video_id(youtube_url)
            if video_id:
                st.session_state.video_id = video_id
                with st.spinner("正在获取字幕..."):
                    transcript = get_transcript(video_id, selected_language)
                    if transcript:
                        st.session_state.transcript = transcript
                
                if transcript:
                    if show_debug:
                        st.write(f"获取到的字幕长度: {len(transcript)}")
                    
                    # 显示字幕预览
                    with st.expander("查看获取到的字幕"):
                        st.text_area("字幕内容", transcript[:2000] + ("..." if len(transcript) > 2000 else ""), height=200)
                    
                    summary, prompt = generate_summary(
                        transcript, 
                        languages[selected_language],
                        api_key,
                        api_endpoint,
                        model_name,
                        api_source,
                        detailed=is_detailed
                    )
                    
                    if summary:
                        if is_detailed:
                            st.session_state.detailed_summary = summary
                            st.session_state.detailed_user_prompt = prompt
                        else:
                            st.session_state.summary = summary
                            st.session_state.user_prompt = prompt
            else:
                custom_error("无效的YouTube URL，请输入正确的视频链接")
    
    with right_col:
        st.subheader("摘要结果")
        
        # 显示结果
        if st.session_state.summary or st.session_state.detailed_summary:
            # 确定要显示的摘要（优先显示最近生成的）
            if st.session_state.detailed_summary and generate_detailed_btn:
                summary = st.session_state.detailed_summary
                prompt = st.session_state.detailed_user_prompt
                title = "视频详细分析"
            elif st.session_state.summary and generate_summary_btn:
                summary = st.session_state.summary
                prompt = st.session_state.user_prompt
                title = "视频概要"
            elif st.session_state.detailed_summary:
                summary = st.session_state.detailed_summary
                prompt = st.session_state.detailed_user_prompt
                title = "视频详细分析"
            else:
                summary = st.session_state.summary
                prompt = st.session_state.user_prompt
                title = "视频概要"
            
            # 显示标题和摘要
            st.markdown(f"### {title}")
            
            if st.session_state.video_id:
                video_url = f"https://www.youtube.com/watch?v={st.session_state.video_id}"
                st.write(f"Video URL: [{video_url}]({video_url})")
                
                # 嵌入视频播放器
                st.video(video_url)
            
            # 创建一个带样式的容器来显示摘要
            st.markdown('<div class="summary-container">', unsafe_allow_html=True)
            st.markdown(summary)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 创建展开器来显示提示词和原始输出
            with st.expander("查看提示词"):
                st.text_area("使用的提示词:", prompt, height=150)
            
            with st.expander("查看原始输出"):
                st.text_area("原始输出:", summary, height=300)
        else:
            st.info("请在左侧输入YouTube视频URL并选择语言，然后点击生成摘要按钮")

if __name__ == "__main__":
    main()