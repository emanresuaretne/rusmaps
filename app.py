import flask as fl
from update import xlsx_downloader, xlsx_to_db, remove_imgs, download_pdns, pdn_to_bins
from map_builder import img_builder, epoch_adder
import sqlite3
import os
import json


def update_func():
    xlsx_downloader()
    xlsx_to_db()
    remove_imgs()
    download_pdns()
    pdn_to_bins()

    global tomes, themes, authors, features
    tomes, themes, authors, features = init()


def init():
    def all_to_var(table_name="Общая"):
        query = f'SELECT * FROM "{table_name}"'
        cur.execute(query)
        return cur.fetchall()

    db = "Банк диалектологических карт.db"
    if db not in os.listdir():
        update_func()
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    maps = all_to_var()
    tomes = {_[1]:
                 {(__[3], __[7], __[0]):
                      {(___[4], ___[8]):
                           all_to_var(f"Том {___[1]}, карта {___[3]}.{___[4]}")
                           if ___[4] else all_to_var(f"Том {_[1]}, карта {___[3]}")
                       for ___ in maps
                       if ___[1] == __[1] and ___[3] == __[3]
                       and ___[11] in ["готова", "сверена"]}
                  for __ in maps if __[1] == _[1]}
             for _ in maps}

    themes = {_[9]:
                 {(__[1], __[3], __[7], __[0]):
                      {(___[4], ___[8]):
                           all_to_var(f"Том {___[1]}, карта {___[3]}.{___[4]}")
                           if ___[4] else all_to_var(f"Том {___[1]}, карта {___[3]}")
                       for ___ in maps
                       if ___[1] == __[1] and ___[3] == __[3] and ___[9] == __[9]
                       and ___[11] in ["готова", "сверена"]}
                  for __ in maps if __[9] == _[9]}
             for _ in maps}

    authors = {_[0]:
                 {(__[1], __[3], __[7]):
                      {(___[4], ___[8]):
                           all_to_var(f"Том {___[1]}, карта {___[3]}.{___[4]}")
                           if ___[4] else all_to_var(f"Том {___[1]}, карта {___[3]}")
                       for ___ in maps
                       if ___[1] == __[1] and ___[3] == __[3] and ___[0] == __[0]
                       and ___[11] in ["готова", "сверена"]}
                  for __ in maps if __[0] == _[0]}
             for _ in maps}

    features = {}
    for tome, chapters in tomes.items():
        for chapter, maps in chapters.items():
            for map_meta, features_meta in maps.items():
                features[f"{tome}_{chapter[0]}{'.' if map_meta[0] else ''}{map_meta[0] if map_meta[0] else ''}"] = \
                    tuple(meta for meta in features_meta)
    conn.close()
    return tomes, themes, authors, features


app = fl.Flask(__name__, static_folder="")
tomes, themes, authors, features = init()


@app.route('/get_epochs_container_template', methods=['POST'])
def get_epochs_container_template():
    form_features = dict(fl.request.form)
    sort_by = form_features.pop('EpochsSortBy')
    epoch = form_features.pop('EpochsPeriod')
    return fl.render_template("epochs_container.html",
                              sort_by=sort_by, epoch=epoch)


@app.route('/get_selector_container_template', methods=['POST'])
def get_selector_container_template():
    form_features = dict(fl.request.form)
    sort_by = form_features.pop('SelectorSortBy')
    epoch = form_features.pop('SelectorPeriod')
    form_features = list(form_features.keys())
    return fl.render_template("selector_container.html",
                              sort_by=sort_by, epoch=epoch,
                              tomes=tomes, themes=themes, authors=authors,
                              form_features=form_features)


@app.route('/get_features_legend_template', methods=['POST'])
def get_features_legend_template():
    form_features = dict(fl.request.form)
    sort_by = form_features.pop('sortBy')
    try:
        cache = json.loads(form_features.pop('cache'))
    except KeyError:
        cache = []
    form_features.pop('period')
    form_features = list(form_features.keys())
    return fl.render_template("features_legend.html", sort_by=sort_by,
                              tomes=tomes, themes=themes, authors=authors,
                              form_features=form_features, cache=cache)


@app.route('/', methods=['GET', 'POST'])
def site():
    sort_by = 'tomes'
    epoch = 'soviet_republics'
    epoch_file = f"{epoch}.png"
    cache = []

    if epoch_file not in os.listdir("maps"):
        epoch_adder(epoch)

    if fl.request.method == 'POST':
        form = fl.request.form
        epoch = form['period']

        entries = [entry for entry in form if entry != "sortBy" and entry.count("_") > 1]

        if entries:
            if any(feature.count("_") == 1 for feature in form): # требуется карта
                for feature in form:
                    if feature.count("_") == 1:
                        file_name = feature
                        break
            else: # требуются признаки
                file_name = ",".join(entries)

            json_cache = f"{file_name}.json"
            map_file = f"{file_name}.png"

            if json_cache in os.listdir("maps"):
                with open(f"maps/{json_cache}", "r") as f:
                    cache = json.load(f)
            else:
                cache = img_builder(entries, features, map_file)
                with open(f"maps/{json_cache}", "w") as f:
                    json.dump(cache, f)

            epoch_file = f"{epoch};{file_name}.png"
            if epoch_file not in os.listdir("maps"):
                epoch_adder(epoch, map_file)

        else:
            epoch_file = f"{epoch}.png"
            if epoch_file not in os.listdir("maps"):
                epoch_adder(epoch)

        response = fl.make_response(fl.jsonify({"file": epoch_file, "cache": cache}), 200)
        return response
    return fl.render_template("site.html", sort_by=sort_by, epoch=epoch, tomes=tomes, themes=themes, authors=authors)


@app.route('/update')
def update():
    update_func()
    return fl.redirect(fl.url_for("site"))


if __name__ == '__main__':
    app.run(use_reloader=False)
