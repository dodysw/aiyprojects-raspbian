import flask, json

app = flask.Flask(__name__)
@app.route("/pisual", methods=['GET', 'POST'])
def pisual():
    body = flask.request.get_json()
    return flask.jsonify(
            message="From pisual: %s" % body,
            notify=True,
            message_format="text"
    )

app.run(use_reloader=False, port=5000)
    
