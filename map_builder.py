import numpy as np
from PIL import Image


def a_sum(fst_arr, scd_arr):
    trd_arr = np.copy(fst_arr)
    a = scd_arr[:, :, 3] == 255
    trd_arr[a] = scd_arr[a]
    return trd_arr


def img_builder(entries, features, file_name):
    def hex_to_rgb(hx):
        return np.array([int(hx[i:i+2], 16) for i in (1, 3, 5)])

    def rgb_to_hex(rgb):
        return '#' + ''.join(f'{int(i):02X}' for i in rgb)

    def npy_to_array(info):
        directory, image = info
        with open(f"{directory}/{image}.npy", 'rb') as f:
            return np.load(f)

    def colour_getter(bool_arr, colours):
        colours_cache = [c for b, c in zip(bool_arr, colours) if b]
        if len(colours_cache) == 0:
            colours_cache.append(np.array([0, 0, 0, 0]))
        elif len(colours_cache) > 1:
            res_colour = np.array(colours_cache).mean(axis=0)
            colours_cache.append(res_colour)
        return colours_cache

    def secondary_colours(secondary, colour):
        res_img = np.zeros((secondary.shape[0], secondary.shape[1], 4))
        colour = np.append(np.array(colour), 255)
        res_img[secondary] = colour
        return res_img

    def average_areals(images, colours):
        res_img = np.zeros((images.shape[1], images.shape[2], 4))

        if len(images) > 1:
            imgs = np.stack(images, axis=2)

            cache = np.unique(imgs.reshape(imgs.shape[0] * imgs.shape[1], -1), axis=0)
            colours_cache = list(map(lambda arr: colour_getter(arr, colours), cache))
            res_colours = [np.append(c[-1], 255) if c[-1].shape[0] == 3 else c[-1] for c in colours_cache]

            for i, unique_array in enumerate(cache):
                mask = np.all(imgs == unique_array, axis=2)
                res_img[mask] = res_colours[i]

        elif len(images) == 1:
            colour = np.append(np.array(colours[0]), 255)
            res_img[images[0]] = colour
            colours_cache = []

        return res_img, colours_cache


    areals = []
    isoglosses = []
    markers = []

    areals_colours = []
    isoglosses_colors = []
    markers_colours = []

    for entry in entries:
        if entry.count("_") == 2:
            tome, mp, feature = entry.split("_")
            tome_map = "_".join([tome, mp])
            feature = int(feature)

            feature_type = features[tome_map][feature][-2]
            colour = features[tome_map][feature][-1]

            if feature_type == 'ареал':
                areals.append((f"maps/Том {tome}, карта {mp}", feature))
                areals_colours.append(colour)
            elif feature_type == 'изоглосса':
                isoglosses.append((f"maps/Том {tome}, карта {mp}", feature))
                isoglosses_colors.append(colour)
            elif feature_type == 'маркеры':
                markers.append((f"maps/Том {tome}, карта {mp}", feature))
                markers_colours.append(colour)

    if areals:
        areals_colours = list(map(hex_to_rgb, areals_colours))
        res, colours_cache = average_areals(np.stack(list(map(npy_to_array, areals))), areals_colours)
    else:
        res = np.zeros((984, 969, 4))

    if isoglosses:
        isoglosses_colors = list(map(hex_to_rgb, isoglosses_colors))
        for isogloss, colour in zip(list(map(npy_to_array, isoglosses)), isoglosses_colors):
            res = a_sum(res, secondary_colours(isogloss, colour))

    if markers:
        markers_colours = list(map(hex_to_rgb, markers_colours))
        for marker, colour in zip(list(map(npy_to_array, markers)), markers_colours):
            res = a_sum(res, secondary_colours(marker, colour))

    res_img = Image.fromarray(res.astype(np.uint8))
    res_img.save(f"maps/{file_name}")

    try:
        colours_cache = [list(map(rgb_to_hex, _)) for _ in colours_cache if len(_) > 1]
    except NameError:
        colours_cache = []
    finally:
        return colours_cache


def epoch_adder(epoch, file_name=None):
    def png_to_array(info):
        directory, image = info
        with Image.open(f"{directory}/{image}").convert("RGBA") as img:
            img.load()
            return np.array(img)

    base_dir = "maps/База"

    layers = ["База"]
    if epoch == "empire_governorates":
        layers += ["Ареал 1914", "Граница_0 1914", "Граница_1 1914", "Граница_2 1914"]
    else:
        layers += ["Ареал XX", "Граница_0 XX", "Граница_1 XX"]
        if epoch == "soviet_oblasts":
            layers.append("Граница_2 XX")
        layers.append("База XX")

    layers = [(base_dir, f"{layer}.png") for layer in layers]

    if file_name:
        layers.insert(2, ("maps", file_name))

    layers_arrays = list(map(png_to_array, layers))

    res = layers_arrays[0]

    for layer in layers_arrays[1:]:
        res = a_sum(res, layer)

    res_img = Image.fromarray(res)
    res_img.save(f"maps/{epoch}{';' if file_name else ''}{file_name if file_name else '.png'}")
