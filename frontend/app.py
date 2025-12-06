# frontend/app.py
import streamlit as st
import requests
import io

# Page config
st.set_page_config(page_title="OSHA Vision AI", layout="wide")

# Custom CSS — black theme
st.markdown("""
<style>
    .main {background-color: #000000; color: white;}
    .stApp {background-color: #000000;}
    h1 {color: #ff006e; text-align: center;}
    .violation-box {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #ff006e;
    }
    .code {font-family: monospace; font-size: 1.1em; color: #ff006e; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

st.title("Construction Safety AI")
st.markdown("### Upload a jobsite photo → Get instant OSHA violations")

uploaded_file = st.file_uploader("Choose image", 
                                 type=["jpg", "jpeg", "png", "webp"])

if uploaded_file:
    # 4:1 layout — annotated image left, violations right
    col_img, col_text = st.columns([3, 1])  # 75% image, 25% violations

    # with col_text:
    #     st.markdown("### VIOLATIONS")

    with col_img:
        with st.spinner("AI is analyzing the site..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                resp = requests.post("http://backend:8000/analyze", files=files, timeout=30)

                if resp.status_code == 200:
                    data = resp.json()
                    annotated_bytes = bytes.fromhex(data["annotated_image_base64"])

                    # Show ONLY the annotated image
                    st.image(annotated_bytes, width="stretch")

                    # Show violations list on the right
                    with col_text:
                        st.markdown("### VIOLATIONS")

                        if data["violations"]:
                            for v in data["violations"]:
                                code = v.get("code", "—")
                                desc = v.get("description", "No description")
                                st.markdown(f"""
                                <div class="violation-box">
                                    <div class="code">{code}</div>
                                    <div>{desc}</div>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.success("No violations detected")

                        st.caption(f"Total: {len(data['violations'])} violation(s) found")

                else:
                    st.error("Backend error")
            
            except Exception as e:
                st.error("Cannot connect to backend. Is it running?")
                st.code("uvicorn backend.main:app --reload")