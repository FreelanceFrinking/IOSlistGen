import streamlit as st
import os
import openai
import backoff
import time

openai.organization = st.secrets["ORGANISATION"]
openai.api_key = st.secrets["API_KEY"]

help = ["Specific industry-related terms and informal language are key to the writing style.",
        "A mix of simple and compound sentences with medium length is consistently used.",
        "The informal and conversational tone is a significant aspect of the style.",
        "A casual and informative voice is consistent throughout the texts.",
        "Standard punctuation marks are used, but do not stand out as a unique characteristic.",
        "Minimal use; occasionally adds humor, but not a defining feature.",
        "Minimal imagery; not a strong characteristic of the style.",
        "Straightforward and clear syntax contributes to the casual and informative voice.",
        "Short, focused paragraphs are consistently used.",
        "Industry news, acquisitions, and insights are central to the writing style.",
        "Third-person perspective is used, but not a standout feature.",
        "Not present in the example texts.",
        "Linear and concise presentation of information is consistent.",
        "Quick and to the point, contributing to the informative nature of the texts.",
        "Not present in the example texts.",
        "Minimal use; occasionally adds personality, but not a defining feature.",
        "Informal language and humor are present, but not a primary characteristic.",
        "News briefs, updates, or industry insights are the preferred formats.",
        "Minimal references to other articles; not a strong characteristic of the style.",
        "Minimal emotional impact; the focus is on conveying information."]



SYS_MESSAGE_1 = """
You are a copywriter, specialized at rewriting longer news stories into one-paragraph news bits. You will be given a list of attributes - delimited by ``` - that describes the writing style. The numbers are the ranks from 1 to 10 that signify how important this attribute is for defining your writing style.
If any "idioms" (a list, seperated by commas) are given, delimited by ==, please try to incorporate them in the text.
You are writing text for a news website about 'industrial outdoor storage'. I will give you a source text - delimited by [ and ] - and I want you to rewrite it. 
After you have written the text, you will be provided with feedback, delimited by < and >. 
If you decide to incorporate the feedback, respond with "Rewitten: " followed by the new text.
If you decide not to use the feedback, reply with only "Finished!".
"""

SYS_MESSAGE_2 = """
You are the owner of a copywriting company. Your task is to review the texts your employees have written. Please provide them with any feedback necessary. Every project has a very specific writing style and conditions to follow, which will be provided to you, delimited by ```. 
If any idioms were given, delimited by ==, then ensure they are incorporated in the text.
The text to review is delimited by < and >. 
If there is no feedback to be given, respond only with "Finished!". 
"""
last_output = ""

def log_text(text):
    st.session_state['log'] += text+ "\n______\n"
    return 

@backoff.on_exception(backoff.expo, openai.error.RateLimitError)
def generate_response(chat_history, input, style_guide, idioms = "", feedback = False):
    if feedback:
        prompt_template = f"""Feedback: <{input}>"""
    else:
        prompt_template = f"""Attribute list: ```{style_guide}```
        Idioms: =={idioms}==
        Source text: [{input}]
        """
    chat_history.append({"role": "user", "content": prompt_template})


    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=chat_history,
        temperature = 0.3
    )
    
    output = completion.choices[0].message.content
    chat_history.append(completion.choices[0].message)
    log_text(f"Style Guide: {style_guide}")
    if feedback:
        log_text(f"Feedback: {input}")
    else:
        log_text(f"Input: {input}")

    log_text(f"Writer: {output}")
    return output, chat_history

@backoff.on_exception(backoff.expo, openai.error.RateLimitError)
def provide_feedback(chat_history, input, style_guide, idioms = ""):
    prompt_template = f"""Attribute list: ````{style_guide}```
    Idioms: =={idioms}==
    Text to review: <{input}>"""
    chat_history.append({"role": "user", "content": prompt_template})
    completion = openai.ChatCompletion.create(
        model=st.session_state['model'],
        messages=chat_history
    )
    
    output = completion.choices[0].message.content
    chat_history.append(completion.choices[0].message)

    return output, chat_history

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True
    
if 'chat_history_writer' not in st.session_state:
        st.session_state['chat_history_writer'] = [{"role": "system", "content": SYS_MESSAGE_1}]
if 'chat_history_manager' not in st.session_state:
        st.session_state['chat_history_manager'] = [{"role": "system", "content": SYS_MESSAGE_2}]  
if 'log' not in st.session_state:
    st.session_state['log'] = ""
if 'score' not in st.session_state:
    st.session_state["score"] = []
if 'model' not in st.session_state:
    st.session_state['model'] = ""
if 'last_output' not in st.session_state:
    st.session_state['last_output'] = ""

if check_password():
    tab1, tab2 = st.tabs(["GPT-3", "GPT-4"])

    with tab1:
        st.session_state['model'] = "gpt-3.5-turbo"
    with tab2:
        st.session_state['model'] = "gpt-4"

    st.title('Content generator IOSList')
    st.header('Upload a news text to generate a newsbit.')
    col1, col2 = st.columns(2)


    scores = list()

    for label, value, help in zip(["Vocabulary", "Sentence structure", "Tone", "Voice", "Punctuation", "Rhetorical devices","Imagery","Syntax","Paragraph structure","Themes",
            "Point of view","Dialogue","Narrative structure","Pace","Repetition", "Idiomatic expressions","Quirks and inconsistencies",
                "Preferences for specific genres or forms", "Intertextuality", "Emotional resonance"], [8,7,9,8,6,4,3,7,8,9,6,1,7,7,2,4,5,9,3,3], help):
        score = col1.slider(label, min_value = 0, max_value = 10, value = value, help = help)
        st.session_state['score'].append(score)

    

    style_guide = f"""Vocabulary: {st.session_state['score'][0]} - Specific industry-related terms and informal language are key to the writing style.
    Sentence structure: {st.session_state['score'][1]} - A mix of simple and compound sentences with medium length is consistently used.
    Tone: {st.session_state['score'][2]} - The informal and conversational tone is a significant aspect of the style.
    Voice: {st.session_state['score'][3]} - A casual and informative voice is consistent throughout the texts.
    Punctuation: {st.session_state['score'][4]} - Standard punctuation marks are used, but do not stand out as a unique characteristic.
    Rhetorical devices: {st.session_state['score'][5]} - Minimal use; occasionally adds humor, but not a defining feature.
    Imagery: {st.session_state['score'][6]} - Minimal imagery; not a strong characteristic of the style.
    Syntax: {st.session_state['score'][7]} - Straightforward and clear syntax contributes to the casual and informative voice.
    Paragraph structure: {st.session_state['score'][8]} - Short, focused paragraphs are consistently used.
    Themes: {st.session_state['score'][9]} - Industry news, acquisitions, and insights are central to the writing style.
    Point of view: {st.session_state['score'][10]} - Third-person perspective is used, but not a standout feature.
    Dialogue: {st.session_state['score'][11]} - Not present in the example texts.
    Narrative structure: {st.session_state['score'][12]} - Linear and concise presentation of information is consistent.
    Pace: {st.session_state['score'][13]} - Quick and to the point, contributing to the informative nature of the texts.
    Repetition: {st.session_state['score'][14]} - Not present in the example texts.
    Idiomatic expressions: {st.session_state['score'][15]} - Minimal use; occasionally adds personality, but not a defining feature.
    Quirks and inconsistencies: {st.session_state['score'][16]} - Informal language and humor are present, but not a primary characteristic.
    Preferences for specific genres or forms: {st.session_state['score'][17]} - News briefs, updates, or industry insights are the preferred formats.
    Intertextuality: {st.session_state['score'][18]} - Minimal references to other articles; not a strong characteristic of the style.
    Emotional resonance: {st.session_state['score'][19]} - Minimal emotional impact; the focus is on conveying information.
    """

    idioms = col2.text_input("Idioms to use: ")
    input = col2.text_area("Enter Text Here", height=275)

    if col2.button('SUBMIT',key='submit_btn'):
        if len(input)<1:
            st.warning("Please input a news article to summarize.")
        else:
            output, st.session_state["chat_history_writer"] = generate_response(st.session_state["chat_history_writer"], input, style_guide, idioms)
            while output.strip() != "Finished!":
                last_output = output
                print(last_output)
                output, st.session_state["chat_history_manager"] = provide_feedback(st.session_state["chat_history_manager"], output, style_guide, idioms)
                print("Feedback: ", output)
                output, st.session_state["chat_history_writer"] = generate_response(st.session_state["chat_history_writer"], output, style_guide, idioms, feedback = True)
            st.session_state["last_output"] = last_output.replace("$", "\\$")

            col2.write(st.session_state['last_output'])

        feedback = col2.text_area("Please give any feedback.")
        if col2.button('SUBMIT',key='submit_feedback'):
            log_text(f"Score: {st.session_state['model']}")
            log_text(f"Score: {st.session_state['score']}")
            log_text(f"Feedback from Matt: {feedback}")
    col2.download_button('Download log', st.session_state['log'] , file_name = f"{time.strftime('%Y%m%d-%H%M%S')}.txt")