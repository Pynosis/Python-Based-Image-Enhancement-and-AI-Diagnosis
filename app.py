import streamlit as st
st.set_page_config(
    page_title="Medical Image Enhancement",
    layout = "wide",
    initial_sidebar_state="expanded"
)
def hideSideBar():
    st.markdown("""<style> [data-testid="stSidebar"]{display:none;}
                [data-testid="collapsedControl"]{display:none;}</style>""",unsafe_allow_html=True)
def hideHeader():
    st.markdown(""" <style>header[data-testid="stHeader"]{display:none}</style>""",unsafe_allow_html=True)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None
if not st.session_state.logged_in:
    hideSideBar()
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("Medical Image Enhancement")
        st.divider()
        tab1, tab2 = st.tabs(["Login","Signup"])
        with tab1:
            with st.form("Login"):
                email = st.text_input("Username or Email")
                password = st.text_input("Password",type="password")
                submitted = st.form_submit_button("Login")
                if submitted:
                    if email == "" or password == "":
                        st.write("Please fill out all the fields")
                    elif email == "doctor@gmail.com" and password == "123":
                        st.session_state.logged_in = True
                        st.session_state.username = "Fizza"
                        st.session_state.role = "Doctor"
                        st.rerun()
                    else:
                        st.error("Incorrect Username or Password")
        with tab2:
            st.write("register")
else:
    hideHeader()
    st.markdown(f"""<div style="
                position: fixed;
                top: 0;
                left:0;
                width: 100%;
                padding: 10px 20px;
                background-color: #028090;
                display: flex;
                justify-content: space-between;
                align-items: center;
                ">
                <div><h1>Painosis</h1></div>
                <div style ="cursor: pointer;
                gap: 30px;
                display: flex" >
                <a>Upload & Enhance</a>
                <a>Results</a>
                <a>History</a>
                <a>Admin</a>
                </div>
                <div style="display:flex; gap:10px;"><p style="margin: 0;">{st.session_state.username}</p>
                <p style="margin: 0";>{st.session_state.role}</p> <a>Logout</a></div></div>""",unsafe_allow_html=True)
