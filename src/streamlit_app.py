import os
from collections.abc import Iterable
import streamlit as st
import types 
import requests
from clarifai.client.user import User
from clarifai_grpc.grpc.api import resources_pb2
from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import resources_pb2, service_pb2, service_pb2_grpc
from clarifai_grpc.grpc.api.status import status_code_pb2

# globals

our_apps= {}
app_datasets = {}
os.environ["CLARIFAI_PAT"] = st.secrets["CLARIFAI_PAT"]
client = User(user_id=st.secrets["clarifai_user_id"])

# from https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso
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


def doapply(data):
    for x in data:
        if isinstance(x,str):
            st.write("apply",x)
            yield x
        else:
            if hasattr(x,"apply"):
                yield from x.apply()
            else:
                st.write("do apply other",x)
                yield x


def act(data):
    if not data:
        return
    for data1 in data:
        
        yield from doapply(data1)  # apply those changes to the api

seen = {}
def myselect(data):
    todo = []
    key = str(data)
    if isinstance(data,str):
        options = st.button(data,
                            key=key + "button"
                            )
    else:
        for f in data:
            todo.append(f)
        if key not in seen:
            st.write("new data",data)
            options = st.multiselect(
                "Please select",todo,key=key)
            seen[key] = options
            st.write("You selected:", options)
            yield options


def decide(data):
    if data:
        if not hasattr(data, '__iter__'):
            #st.write("The object is iterable.")
            if not isinstance(data, Iterable):
                #st.write("The object is iterable.")
                #else:
                name = ""
                if hasattr(data,"name"):
                    name = data.name()
                    
                data = [ "Just " + name + str(type(data)) + " debug "+ str(data) ]
                yield myselect(data)  # let the user select which ones
                return
            
            #for data1 in data:
            yield from myselect([data1 for data1 in data])  # let the user select which ones

def summarize(data):
    #if isinstance(data, generato):
    if isinstance(data, Iterable):
        if isinstance(data, types.GeneratorType):
            pass
        else:
            st.write("Sum Object is iterable", type(data).__name__, data, )
        for x in data:
            yield x
    else:
        st.write("Sum Object not an iterable")
        yield data

        #for x in data:
        #yield x
def sort(data):
    if isinstance(data, Iterable):
        if isinstance(data, types.GeneratorType):
            pass
        else:

            st.write("Sort Object is iterable",type(data).__name__,data)
        for x in data:
            yield x
    else:
        st.write("Sort Object not an iterable",data)
        yield data

    #for x in data:
    #    yield x
from collections.abc import Iterable

def filtering(data):
    if isinstance(data,str):
        yield data
        return
    if isinstance(data, Iterable):

        if isinstance(data, types.GeneratorType):
            pass
        else:            
            st.write("Filtering Object is iterable",type(data).__name__,data)
            
        for x in data:
            yield x
    else:
        st.write("Filtering Object not an iterable", data)
        yield data
        
def orient(data):
    yield from summarize(sort(filtering(data)))  # show a summary of the data


def apps():
    # list the apps we have access to
    for app in our_apps:
        yield app

def datasets(app):
    if app.name in app_datasets:
        st.write ("DEBUG1",app.name)
        for name in app_datasets[app.name]:
            st.write ("DEBUG2",app.name, "in", app_datasets)
            yield name
    else:
        st.write ("DEBUG",app.name, "not in", app_datasets)

def inputs(dataset):
    for x in ("inputa","inputb"):
        yield dataset + x
    
def unassigned_inputs(app):

    PAT = st.secrets["CLARIFAI_PAT"]
    USER_ID =st.secrets["clarifai_user_id"]
    channel = ClarifaiChannel.get_grpc_channel()
    stub = service_pb2_grpc.V2Stub(channel)
    metadata = (('authorization', 'Key ' + PAT),)
    userDataObject = resources_pb2.UserAppIDSet(user_id=USER_ID, app_id=app.id)
    stream_inputs_response = stub.StreamInputs(
        service_pb2.StreamInputsRequest(
            user_app_id=userDataObject,
            per_page=3,
        ),
        metadata=metadata
    )

    if stream_inputs_response.status.code != status_code_pb2.SUCCESS:
        yield({"status":stream_inputs_response.status})
        raise Exception("Stream inputs failed, status: " + stream_inputs_response.status.description)

    for input_object in stream_inputs_response.inputs:

        data2 =  requests.get(input_object.data.text.url)
        value =   data2.text
        yield({
            "type": "input",
            #"res": data2.resu
            "url": input_object.data.text.url,
            "value":             value})
    

def observe():
    for app in apps():
        st.write("App",app.name)

        yield from unassigned_inputs(app)
                
        for dataset in datasets(app):
            st.write("Dataset",dataset)
            for input in inputs(dataset):
                yield {"dataset": [ app , dataset, input ]}
        #for input in unassigned_inputs(dataset):

        #    yield [ app , dataset, input ]

def ooda():
    for sample in observe():
        samples = []
        for oriented in orient(sample):
            st.write("orient",oriented)
            samples.append(oriented)
        for decision in decide(samples):
            yield from act(decision)


# taken from https://gist.githubusercontent.com/iankelk/7e46c9935442ba01853b1689ff4a5038/raw/a261f99e6dd9cef6cc3d9ee04648df40232072d9/C-everything.py
def load_pat():
    if "CLARIFAI_PAT" not in st.secrets:
        st.error("You need to set the CLARIFAI_PAT in the secrets.")
        st.stop()
    return st.secrets.CLARIFAI_PAT


def get_default_models():
    if "DEFAULT_MODELS" not in st.secrets:
        st.error("You need to set the default models in the secrets.")
        st.stop()
    models_list = [x.strip() for x in st.secrets.DEFAULT_MODELS.split(",")]
    models_map = {}
    select_map = {}
    for i in range(len(models_list)):
        m = models_list[i]
        id, rem = m.split(":")
        author, app = rem.split(";")
        models_map[id] = {}
        models_map[id]["author"] = author
        models_map[id]["app"] = app
        select_map[id + " : " + author] = id
    return models_map, select_map



def main():
    global our_apps
    st.set_page_config(layout="wide")

    our_apps = client.list_apps()
    #if check_password():
    if True: # skip password for now
        for x in ooda():
            if isinstance(x,str):
                st.write("str",x)
            else:
                if hasattr(x,"apply"):
                    for x in  x.apply():
                        st.write("app",x)
                    else:
                        st.write("other",x)
                        
    models = {}
    dataset_index = {}

    for app in our_apps:
        datasets = app.list_datasets()
        for ds in datasets:
            name = ds.dataset_info.id
            if app not in app_datasets:
                app_datasets[app.name]={}
            if name not in app_datasets[app.name]:
                app_datasets[app.name][name] = ds
        
            dataset_index[name] = ds
    for model_name in models:
        idn = "cf_dataset_" + model_name.lower()
        if idn not in dataset_index:
            dataset = app.create_dataset(dataset_id=idn)
        else:
            models[model_name].set_dataset(dataset_index[idn])
        models[model_name].sync()


if __name__ == "__main__":
    main()
