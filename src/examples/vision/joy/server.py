import flask, json, os

app = flask.Flask(__name__)

data_filename =  'hchat_notify_data.json'

@app.route("/pisual", methods=['GET', 'POST'])
def pisual():
    body = flask.request.get_json()
    data = None
    if os.path.isfile(data_filename):
        with open(data_filename) as f:
            data = json.load(f)
    return flask.jsonify(
            message="Happiness index data: %s" % data,
            notify=True,
            message_format="text"
    )

app.run(use_reloader=False, port=5000)
    
