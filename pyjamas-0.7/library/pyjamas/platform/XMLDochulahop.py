def create_xml_doc(text):
    parser = get_main_frame().getDOMParser()
    return parser.parseFromString(text, "text/xml")
