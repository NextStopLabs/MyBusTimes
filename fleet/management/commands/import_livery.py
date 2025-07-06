import re
from django.core.management.base import BaseCommand
from fleet.models import liverie
from main.models import CustomUser
import csv

manual_liveries = {
    "Clivery-1": {
        "background_color": "#ff0000"
    },
    "Clivery-2": {
        "background_color": "#ff6200"
    },
    "Clivery-3": {
        "background_color": "#ffc800"
    },
    "Clivery-4": {
        "background_color": "#6fff00"
    },
    "Clivery-5": {
        "background_color": "#57ad15"
    },
    "Clivery-6": {
        "background_color": "#00ccff"
    },
    "Clivery-7": {
        "background_color": "#005eff"
    },
    "Clivery-8": {
        "background_color": "#6f00ff"
    },
    "Clivery-9": {
        "background_color": "#a600ff"
    },
    "Clivery-10": {
        "background_color": "#f200ff"
    },
    "Olivery-1": {
        "background_color": "#f475ff"
    },
    "Olivery-2": {
        "background_color": "#ff7817"
    },
    "Olivery-3": {
        "background_color": "#ff3f40",
        "background_image": "radial-gradient(circle at 165% 50%, #ff3f40ff 50%, transparent 50.05%), radial-gradient(circle at 128% 50%, #950001ff 50%, transparent 50.05%)"
    },
    "Glivery-1": {
        "background_color": "#119aff",
        "background_image": "linear-gradient(145deg, #05004dff 39%, transparent 39.05%), linear-gradient(30deg, #05004dff 41%, transparent 41.05%), linear-gradient(180deg, #05004dff 30%, transparent 30.05%), linear-gradient(0deg, #05004dff 36%, transparent 36.05%)"
    },
    "Glivery-2": {
        "background_color": "#03fc41",
        "background_image": "linear-gradient(145deg, #05004dff 39%, transparent 39.05%), linear-gradient(30deg, #05004dff 41%, transparent 41.05%), linear-gradient(180deg, #05004dff 30%, transparent 30.05%), linear-gradient(0deg, #05004dff 36%, transparent 36.05%)"
    },
    "Glivery-3": {
        "background_color": "#F63C3C",
        "background_image": "linear-gradient(145deg, #05004dff 39%, transparent 39.05%), linear-gradient(30deg, #05004dff 41%, transparent 41.05%), linear-gradient(180deg, #05004dff 30%, transparent 30.05%), linear-gradient(0deg, #05004dff 36%, transparent 36.05%)"
    },
    "Nlivery-1": {
        "background_color": "#00989a",
        "background_image": "radial-gradient(circle at -60% 50%, #aae4ffff 60%, transparent 20.05%)"
    },
    "livery-01": {
        "background": "linear-gradient(to top, #333 25%, #ffba00ff 25%, #ffba00ff 75%, #333 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-02": {
        "background": "linear-gradient(to top, #333333 15%, #ffba00ff 12%, #ffba00ff 45%, #333333 45%, #333333 56%, #ffba00ff 56%, #ffba00ff 85%, #333333 80%)"
    },
    "livery-03": {
        "background_color": "#ffba00ff",
        "background_image": "linear-gradient(-180deg, #333333ff 15%, transparent 15.05%), linear-gradient(-180deg, #ffba00ff 40%, transparent 40.05%), linear-gradient(-180deg, #333333ff 55%, transparent 55.05%), linear-gradient(0deg, #333333ff 15%, transparent 15.05%), radial-gradient(circle at 9% 64%, #00c623ff 7%, transparent 7.05%)"
    },
    "livery-04": {
        "background_color": "#ffba00ff",
        "background_image": "linear-gradient(-180deg, #333333ff 15%, transparent 15.05%), linear-gradient(-180deg, #ffba00ff 40%, transparent 40.05%), linear-gradient(-180deg, #333333ff 55%, transparent 55.05%), linear-gradient(0deg, #333333ff 15%, transparent 15.05%), radial-gradient(circle at 9% 64%, #0ba07fff 7%, transparent 7.05%)"
    },
    "livery-05": {
        "background_color": "#ffba00ff",
        "background_image": "linear-gradient(-180deg, #333333ff 15%, transparent 15.05%), linear-gradient(-180deg, #ffba00ff 40%, transparent 40.05%), linear-gradient(-180deg, #333333ff 55%, transparent 55.05%), linear-gradient(0deg, #333333ff 15%, transparent 15.05%), radial-gradient(circle at 9% 64%, #4ebd46ff 7%, transparent 7.05%)"
    },
    "livery-06": {
        "background_color": "#ffba00ff",
        "background_image": "linear-gradient(-180deg, #333333ff 15%, transparent 15.05%), linear-gradient(-180deg, #ffba00ff 40%, transparent 40.05%), linear-gradient(-180deg, #333333ff 55%, transparent 55.05%), linear-gradient(0deg, #333333ff 15%, transparent 15.05%), radial-gradient(circle at 9% 64%, #4691bdff 7%, transparent 7.05%)"
    },
    "livery-07": {
        "background_color": "#ffba00ff",
        "background_image": "linear-gradient(-180deg, #333333ff 15%, transparent 15.05%), linear-gradient(-180deg, #ffba00ff 40%, transparent 40.05%), linear-gradient(-180deg, #333333ff 55%, transparent 55.05%), linear-gradient(0deg, #333333ff 15%, transparent 15.05%), radial-gradient(circle at 9% 64%, #bd46b0ff 7%, transparent 7.05%)"
    },
    "livery-08": {
        "background_color": "#ffba00ff",
        "background_image": "linear-gradient(-180deg, #333333ff 15%, transparent 15.05%), linear-gradient(-180deg, #ffba00ff 40%, transparent 40.05%), linear-gradient(-180deg, #333333ff 55%, transparent 55.05%), linear-gradient(0deg, #333333ff 15%, transparent 15.05%), radial-gradient(circle at 9% 64%, #e32b2bff 7%, transparent 7.05%)"
    },
    "livery-09": {
        "background_color": "#ffba00ff",
        "background_image": "linear-gradient(-180deg, #333333ff 15%, transparent 15.05%), linear-gradient(-180deg, #ffba00ff 40%, transparent 40.05%), linear-gradient(-180deg, #333333ff 55%, transparent 55.05%), linear-gradient(0deg, #333333ff 15%, transparent 15.05%), radial-gradient(circle at 9% 64%, #25802cff 7%, transparent 7.05%)"
    },
    "livery-010": {
        "background_color": "#ffba00ff",
        "background_image": "linear-gradient(-180deg, #333333ff 15%, transparent 15.05%), linear-gradient(-180deg, #ffba00ff 40%, transparent 40.05%), linear-gradient(-180deg, #333333ff 55%, transparent 55.05%), linear-gradient(0deg, #333333ff 15%, transparent 15.05%), radial-gradient(circle at 9% 64%, #0283fcff 7%, transparent 7.05%), radial-gradient(circle at 25% 64%, #8902fcff 7%, transparent 7.05%)"
    },
    "livery-011": {
        "background_color": "#ffba00",
        "background_image": "radial-gradient(circle at 19% 29%, #8902fcff 7.5%, transparent 5.05%), radial-gradient(circle at 9% 29%, #0283fcff 6.5%, transparent 5.05%), linear-gradient(-249deg, #ffba00ff 33%, transparent 23.05%), linear-gradient(-180deg, #333333ff 20%, transparent 20.05%), linear-gradient(0deg, #333333ff 20%, transparent 20.05%)"
    },
    "livery-012": {
        "background_color": "#ffba00",
        "background_image": "radial-gradient(circle at 12% 20%, #bd46b0ff 7%, transparent 5.05%), linear-gradient(-249deg, #ffba00ff 33%, transparent 23.05%), linear-gradient(-180deg, #333333ff 20%, transparent 20.05%), linear-gradient(0deg, #333333ff 20%, transparent 20.05%)"
    },
    "livery-013": {
        "background_color": "#ffba00",
        "background_image": "radial-gradient(circle at 85% 55%, #00c623ff 9%, transparent 5.05%), linear-gradient(-180deg, #333333ff 20%, transparent 20.05%), linear-gradient(0deg, #333333ff 20%, transparent 20.05%)"
    },
    "livery-014": {
        "background_color": "#ffba00",
        "background_image": "radial-gradient(circle at 70% 55%, #0283fc 10%, transparent 5.05%), radial-gradient(circle at 85% 55%, #8902fc 9%, transparent 5.05%), linear-gradient(-180deg, #333 20%, transparent 20.05%), linear-gradient(0deg, #333 20%, transparent 20.05%)"
    },
    "livery-015": {
        "background_color": "#ffba00",
        "background_image": "linear-gradient(-230deg, #ffba00ff 50%, transparent 50.05%), linear-gradient(0deg, #333333ff 30%, transparent 30.05%)"
    },
    "livery-016": {
        "background_color": "#ffba00",
        "background_image": "radial-gradient(circle at 85% 55%, #4ebd46ff 9%, transparent 5.05%), linear-gradient(-180deg, #333333ff 20%, transparent 20.05%), linear-gradient(0deg, #333333ff 20%, transparent 20.05%)"
    },
    "livery-017": {
        "background_color": "#ffba00",
        "background_image": "radial-gradient(circle at 12% 20%, #4ebd46ff 7%, transparent 5.05%), linear-gradient(-249deg, #ffba00ff 33%, transparent 23.05%), linear-gradient(-180deg, #333333ff 20%, transparent 20.05%), linear-gradient(0deg, #333333ff 20%, transparent 20.05%)"
    },
    "livery-018": {
        "background_color": "#ffba00",
        "background_image": "radial-gradient(circle at 15% 55%, #4ebd46 9%, transparent 5.05%), linear-gradient(-180deg, #333 20%, transparent 20.05%), linear-gradient(0deg, #333 20%, transparent 20.05%)"
    },
    "livery-019": {
        "background_color": "#ffba00",
        "background_image": "radial-gradient(circle at 15% 55%, #4691bdff 9%, transparent 5.05%), linear-gradient(-180deg, #333 20%, transparent 20.05%), linear-gradient(0deg, #333 20%, transparent 20.05%)"
    },
    "livery-1": {
        "color": "#fff",
        "fill": "#fff",
        "background": "linear-gradient(#f4a406 33%, #e86628 33% 66%, #5589c3 66%)"
    },
    "livery-2": {
        "background": "#ffd600"
    },
    "livery-3": {
        "color": "#fff",
        "fill": "#fff",
        "background": "linear-gradient(#a5a5a5 25%, #21abe8 25% 50%, #a5a5a5 50% 75%, #21abe8 75%)"
    },
    "livery-4": {
        "background": "linear-gradient(#fff 75%, #0eab4c 75%)"
    },
    "livery-5": {
        "stroke": "#e9a804",
        "background": "linear-gradient(#e9a804 66%, #d32527 66%)"
    },
    "livery-6": {
        "background": "linear-gradient(#fff 75%, #181669 75%)"
    },
    "livery-7": {
        "background": "linear-gradient(#e0effa 53%, #a9b8e3 53% 73%, #f571bb 73% 80%, #5768a0 80%)"
    },
    "livery-8": {
        "stroke": "#fff",
        "background": "linear-gradient(#0000 80%, #0f6db4 80%), radial-gradient(circle at 0 0, #fff 60%, #f79f48 60% 70%, #ea2639 70%)"
    },
    "livery-9": {
        "stroke": "#fdc52e",
        "background": "linear-gradient(#c00000 25%, #fdc52e 25% 75%, #c00000 75%)"
    },
    "livery-10": {
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-11": {
        "color": "#fff",
        "fill": "#fff",
        "background": "linear-gradient(#032e60 66%, #757983 66%)"
    },
    "livery-12": {
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#032e60",
        "background": "linear-gradient(#032e60 66%, #fff200 66%)"
    },
    "livery-13": {
        "stroke": "#fafbe1",
        "background": "linear-gradient(#ec1b22 50%, #fafbe1 50%)"
    },
    "livery-14": {
        "color": "#7d287d",
        "fill": "#7d287d",
        "stroke": "#fdee00",
        "background": "linear-gradient(#fdee00 66%, #7d287d 66%)"
    },
    "livery-15": {
        "color": "#fff",
        "fill": "#fff",
        "background": "#fb0d1b"
    },
    "livery-16": {
        "stroke": "#fff",
        "background": "linear-gradient(#fff 66%, #780121 66%)"
    },
    "livery-17": {
        "background": "linear-gradient(90deg, #e9e689 60%, #0268ee 60%)"
    },
    "livery-18": {
        "background": "#f9e300"
    },
    "livery-19": {
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#53565a",
        "background": "linear-gradient(#53565a 40%, #f4ea5d 40% 60%, #53565a 60%)"
    },
    "livery-20": {
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000",
        "background": "linear-gradient(#feed00 50%, #000 50%)"
    },
    "livery-21": {
        "background_color": "#fcedb2",
        "background_image": "linear-gradient(-180deg, #00d792ff 30%, transparent 30.05%)"
    },
    "livery-22": {
        "background": "radial-gradient(130% 145% at 10% 25%, #0480 60%, #e01 60%), radial-gradient(circle at 100% 140%, #048 92%, #e01 92%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-23": {
        "background_color": "#57585a"
    },
    "livery-24": {
        "background": "linear-gradient(90deg, #9c2 45%, #0000 45%, #0000 55%, #06b 55%), linear-gradient(180deg, #e01 85%, #06b 85%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#0065ba"
    },
    "livery-25": {
        "background": "radial-gradient(ellipse at 20% 134%, #006a2e 30%, transparent 30%), radial-gradient(ellipse at 51% 16%, #a1c616 60%, transparent 0%), linear-gradient(80deg, #a1c616 0%, #a1c616 31%, transparent 10%), radial-gradient(ellipse at 50% 17%, #a1c616 60%, #0000 10%), radial-gradient(ellipse at 50% 16%, #006a2e 60%, #006a2e 0%)",
        "stroke": "#a1c616"
    },
    "livery-26": {
        "background": "radial-gradient(ellipse at 20% 134%, #0055bb 30%, transparent 30%), radial-gradient(ellipse at 51% 16%, #11bbff 60%, transparent 0%), linear-gradient(80deg, #11bbff 0%, #11bbff 31%, transparent 10%), radial-gradient(ellipse at 50% 17%, #11bbff 60%, #0000 10%), radial-gradient(ellipse at 50% 16%, #0055bb 60%, #0055bb 0%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-27": {
        "background": "linear-gradient(to top, #40A651 34%, #00899A 34%, #00899A 67%, #1F65A0 67%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-28": {
        "background": "radial-gradient(circle at -20% 25%, #25B0CF 48%, #64CDE5 48%, #64CDE5 56%, #FFFF 56%, #FFFF 62%, #25B0CF 62%)",
        "stroke": "#25B0CF"
    },
    "livery-29": {
        "background": "linear-gradient(to top, #F4EE35 50%, #292B69 50%)",
        "stroke": "#F4EE35"
    },
    "livery-30": {
        "background": "#000"
    },
    "livery-31": {
        "background_color": "#ffac00",
        "background_image": "linear-gradient(-90deg, #000000ff 45%, transparent 45.05%), linear-gradient(-90deg, #f9edadff 60%, transparent 60.05%)"
    },
    "livery-32": {
        "background_color": "#acaba5",
        "background_image": "linear-gradient(-125deg, #0094c0ff 35%, transparent 35.05%), linear-gradient(-125deg, #acaba5ff 43%, transparent 43.05%), linear-gradient(-125deg, #291e64ff 57%, transparent 57.05%)"
    },
    "livery-33": {
        "background_color": "linear-gradient(#fff 66%, #e20177 66%, transparent 83%, #003473 83%)"
    },
    "livery-34": {
        "background_color": "#ffffff",
        "background_image": "radial-gradient(circle at -25% -50%, #ffffffff 53%, transparent 53.05%), radial-gradient(circle at -55% -95%, #00167dff 65%, transparent 65.05%), radial-gradient(circle at -71% -105%, #ffffffff 70%, transparent 70.05%), radial-gradient(circle at -87% -110%, #00167dff 75%, transparent 75.05%), radial-gradient(circle at -109% -130%, #ffffffff 80%, transparent 80.05%), radial-gradient(circle at -146% -157%, #00167dff 85%, transparent 85.05%), radial-gradient(circle at -210% -200%, #ff1c21ff 90%, transparent 90.05%), linear-gradient(180deg, #ff1c21ff 22%, transparent 22.05%)"
    },
    "livery-35": {
        "background": "radial-gradient(circle at 50% 200%, #3F8B2E 70%, #AEBD59 50%, #AEBD59 56%, #AEBD59 56%)"
    },
    "livery-36": {
        "background": "radial-gradient(ellipse at 23% 140%, #ff2222 31%, transparent 31%), radial-gradient(circle at 51% 42%, #ffffcb 49%, transparent 0%), linear-gradient(109deg, #ffffcb 1%, #ffffcb 46%, transparent 10%), linear-gradient(3deg, #f22 20%, #0000 20%), radial-gradient(circle at 45% 24%, #000 60%, transparent 10%), linear-gradient(to top, #f22 20%, #f22 20%)",
        "stroke": "#ffffcb"
    },
    "livery-37": {
        "background": "#000"
    },
    "livery-38": {
        "background": "linear-gradient(90deg, #8e4 55%, #04a0 55%), radial-gradient(circle at 52% 50%, #8e4 52%, #0000 52%), radial-gradient(circle at 55% 41.8%, #18e 58%, #0000 58%), #04a"
    },
    "livery-39": {
        "background": "radial-gradient(ellipse at 23% 140%, #ff2222 31%, transparent 31%), radial-gradient(circle at 51% 42%, #ffffcb 49%, transparent 0%), linear-gradient(109deg, #ffffcb 1%, #ffffcb 46%, transparent 10%), linear-gradient(3deg, #f22 20%, #0000 20%), radial-gradient(circle at 45% 24%, #bb88cc 60%, transparent 10%), linear-gradient(to top, #f22 20%, #f22 20%)",
        "stroke": "#ffffcb"
    },
    "livery-40": {
        "background": "radial-gradient(ellipse at 23% 140%, #ff2222 31%, transparent 31%), radial-gradient(circle at 51% 42%, #ffffcb 49%, transparent 0%), linear-gradient(109deg, #ffffcb 1%, #ffffcb 46%, transparent 10%), linear-gradient(3deg, #f22 20%, #0000 20%), radial-gradient(circle at 45% 24%, #005599 60%, transparent 10%), linear-gradient(to top, #f22 20%, #f22 20%)",
        "stroke": "#ffffcb"
    },
    "livery-41": {
        "background": "linear-gradient(90deg, #ed8 55%, #04a0 55%), radial-gradient(circle at 52% 50%, #ed8 52%, #0000 52%), radial-gradient(circle at 55% 41.8%, #d19 58%, #0000 58%), #405"
    },
    "livery-42": {
        "background": "radial-gradient(circle at 0% 12%, #C7B089 55.5%, transparent 56%), radial-gradient(circle at top left, #C7B089 55.5%, transparent 56%, transparent 63%, #195e8f 63.5%), linear-gradient(45deg, #f57c00 0%, #FEF3AF 75%)",
        "stroke": "#C7B089"
    },
    "livery-43": {
        "background": "radial-gradient(circle at 15% 0%, transparent 70%, #172450 70%), linear-gradient(to top, #172450 20%, transparent 20%), radial-gradient(ellipse 100% 50% at 15% 77%, #ffffff 30%, transparent 30%), radial-gradient(ellipse 95% 50% at 10% 73%, #ffffff 30%, transparent 30%), radial-gradient(circle at 15% 0%, transparent 70%, #172450 70%), radial-gradient(circle at -25% 125%, #ffffff 45%, #FEAC1C 45%, #FEAC1C 50%, transparent 50%), linear-gradient(to top, transparent 52%, #0672BA 52%), radial-gradient(circle at 60% 15%, #0672BA 45%, #FEAC1C 45%, #FEAC1C 50%, transparent 50%), linear-gradient(to top, #0F6DB4 20%, #ffffff 20%)",
        "stroke": "#ffffff"
    },
    "livery-44": {
        "background": "linear-gradient(to top, #692381 25%, #ACD748 25%, #ACD748 75%, #692381 75%)",
        "stroke": "#ACD748"
    },
    "livery-45": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, #fff 30%)",
        "stroke": "#ffffff"
    },
    "livery-46": {
        "background_color": "#ffffff",
        "background_image": "radial-gradient(circle at -18% -61%, #ffffffff 50%, transparent 50.05%), radial-gradient(circle at -13% -48%, #00167dff 55%, transparent 55.05%), radial-gradient(circle at -4% -33%, #535353ff 55%, transparent 55.05%), radial-gradient(circle at 10% -13%, #00167dff 55%, transparent 55.05%), radial-gradient(circle at 25% 3%, #535353ff 55%, transparent 55.05%), radial-gradient(circle at 41% 14%, #00167dff 55%, transparent 55.05%), radial-gradient(circle at 46% 35%, #ff1c21ff 65%, transparent 65.05%), linear-gradient(180deg, #ff1c21ff 35%, transparent 35.05%), linear-gradient(76deg, #ff1c21ff 50%, transparent 50.05%)"
    },
    "livery-47": {
        "background_color": "#2b7071",
        "background_image": "radial-gradient(circle at 44% 92%, #ecca8eff 15%, transparent 15.05%), radial-gradient(circle at 41% 94%, #765728ff 16%, transparent 16.05%), linear-gradient(90deg, #2b7071ff 44%, transparent 44.05%), linear-gradient(0deg, #ecca8eff 30%, transparent 30.05%)"
    },
    "livery-48": {
        "background": "linear-gradient(to top, #C00D0E 50%, #C2C2C2 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-49": {
        "background": "linear-gradient(to right, #E73323 34%, #A52A23 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-50": {
        "background_color": "#88119d",
        "background_image": "linear-gradient(180deg, #b1b0aeff 55%, transparent 55.05%), linear-gradient(0deg, #b1b0aeff 25%, transparent 25.05%)"
    },
    "livery-51": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(244deg, #ff0000ff 31%, transparent 31.05%), radial-gradient(circle at 55% 35%, #ffffffff 46%, transparent 46.05%), radial-gradient(circle at 44% 35%, #10aab5 44%, transparent 44.05%), radial-gradient(circle at -4% 50%, #002affff 50%, transparent 50.05%), radial-gradient(circle at 40% 180%, #002affff 50%, transparent 50.05%)"
    },
    "livery-52": {
        "background": "linear-gradient(to top, #163730 20%, transparent 20%), radial-gradient(circle at top left, transparent 60%, #6B902A 60%, #6B902A 70%, #163730 70%), radial-gradient(circle at bottom center, #fff 84%, #6B902A 84%, #6B902A 92%, #163730 92%)",
        "stroke": "#FFFFFF"
    },
    "livery-53": {
        "background_color": "#b3e2ff",
        "background_image": "linear-gradient(0deg, #00eb5aff 25%, transparent 25.05%), radial-gradient(circle at 50% 15%, #b3e2ffff 50%, transparent 50.05%), radial-gradient(circle at -19% 50%, #00eb5aff 50%, transparent 50.05%)"
    },
    "livery-54": {
        "background": "linear-gradient(to right, #ffffff 34%, #82b958 34%, #82b958 67%, #07498a 67%)",
        "stroke": "#ffffff"
    },
    "livery-55": {
        "background": "linear-gradient(to right, #00B5F1 40%, #0042B5 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-56": {
        "background": "linear-gradient(to top, #2B5D64 20%, transparent 20%), radial-gradient(circle at top left, #29BFCF 25%, transparent 25%), radial-gradient(at top left, #F0F0C8 35%, transparent 35%), linear-gradient(to top, #FFD800 20%, #FFD800 24%, transparent 0%), radial-gradient(circle at 0 20%, #29BFCF 35%, #29BFCF 40%)"
    },
    "livery-57": {
        "background": "radial-gradient(circle at -30% 25%, #3DB8D9 48%, #A9EEF0 48%, #A9EEF0 54%, #40C7DA 54%, #40C7DA 60%, #25A9D1 60%, #25A9D1 66%, #0B4A76 56%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-58": {
        "background": "#121116"
    },
    "livery-59": {
        "background": "linear-gradient(to top, #0A5282 23%, #F4EBC3 23%, #F4EBC3 34%, #6A8A99 34%, #6A8A99 56%, #F4EBC3 56%)",
        "stroke": "#F4EBC3"
    },
    "livery-60": {
        "background": "linear-gradient(to top, #C71A26 43%, #F3F1E5 43%, #F3F1E5 47%, #2B3F8A 47%, #2B3F8A 58%, #F3F1E5 58%)",
        "stroke": "#F3F1E5"
    },
    "livery-61": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(0deg, #ffffffff 37%, transparent 37.05%), linear-gradient(0deg, #ffd500ff 45%, transparent 45.05%), linear-gradient(0deg, #007bffff 55%, transparent 55.05%)"
    },
    "livery-62": {
        "background": "linear-gradient(to top, #0A5282 13%, #F4EBC3 13%, #F4EBC3 19%, #6A8A99 19%, #6A8A99 32%, #F4EBC3 32%, #F4EBC3 50%, #0A5282 50%, #0A5282 63%, #F4EBC3 63%, #F4EBC3 69%, #6A8A99 69%, #6A8A99 82%, #F4EBC3 82%)",
        "stroke": "#F4EBC3"
    },
    "livery-63": {
        "background_color": "#4cebee",
        "background_image": "linear-gradient(60deg, #c2b8f7ff 28%, transparent 28.05%), radial-gradient(circle at 93% -2%, #c2b8f7ff 12%, transparent 12.05%), radial-gradient(circle at 102% -18%, #4cebeeff 25%, transparent 25.05%), radial-gradient(circle at 87% 0%, #733fdfff 22%, transparent 22.05%), radial-gradient(circle at 91% 6%, #4cebeeff 63%, transparent 63.05%), linear-gradient(60deg, #733fdfff 43%, transparent 43.05%)"
    },
    "livery-64": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(90deg, #008060ff 30%, transparent 30.05%), linear-gradient(18deg, #008060ff 36%, transparent 36.05%)"
    },
    "livery-65": {
        "background": "linear-gradient(to right, #673AB7 12%, #ffffff 12%, #ffffff 89%, #673AB7 89%)"
    },
    "livery-66": {
        "background": "linear-gradient(to top, #1C559C 34%, #ffffff 34%, #ffffff 67%, #55C232 67%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-67": {
        "background": "linear-gradient(to top, #15601E 50%, #ffffff 50%)",
        "stroke": "#ffffff"
    },
    "livery-68": {
        "background": "linear-gradient(to top, #0A5282 25%, #F4EBC3 25%)"
    },
    "livery-69": {
        "background": "linear-gradient(0deg, #09302d 15%, #d4d1b8 8%, #d4d1b8 20%, #1c6017 12%, #1c6017 50%, #1c6017 72%, #1c6017 80%, #d4d1b8 0%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-70": {
        "background": "#6525B3"
    },
    "livery-71": {
        "background_color": "#10009f",
        "background_image": "linear-gradient(90deg, #ffffffff 40%, transparent 40.05%), linear-gradient(-90deg, #ffffffff 40%, transparent 40.05%)"
    },
    "livery-72": {
        "background_image": "linear-gradient(244deg, rgb(42, 159, 0) 31%, transparent 31.05%), radial-gradient(circle at 55% 35%, rgb(255, 255, 255) 46%, transparent 46.05%), radial-gradient(circle at 44% 35%, rgb(16, 170, 181) 44%, transparent 44.05%), radial-gradient(circle at -4% 50%, rgb(0, 42, 255) 50%, transparent 50.05%), radial-gradient(circle at 40% 180%, rgb(0, 42, 255) 50%, transparent 50.05%)"
    },
    "livery-73": {
        "background_color": "#b3e2ff",
        "background_image": "linear-gradient(65deg, #00eb5aff 40%, transparent 40.05%), linear-gradient(-115deg, #00eb5aff 40%, transparent 40.05%), linear-gradient(0deg, #00eb5aff 30%, transparent 30.05%)"
    },
    "livery-74": {
        "background_color": "#ffffff",
        "background_image": "radial-gradient(circle at 106% 50%, #0510ffff 19%, transparent 19.05%), linear-gradient(-65deg, #ffffffff 50%, transparent 50.05%), linear-gradient(-65deg, #ff0d02ff 60%, transparent 60.05%), linear-gradient(-65deg, #0510ffff 70%, transparent 70.05%)"
    },
    "livery-75": {
        "background_color": "#4cebee",
        "background_image": "linear-gradient(60deg, #c2b8f7ff 28%, transparent 28.05%), radial-gradient(circle at 126% 50%, #c2b8f7ff 40%, transparent 40.05%), radial-gradient(circle at 99% -2%, #733fdfff 34%, transparent 34.05%), radial-gradient(circle at 91% 6%, #4cebeeff 63%, transparent 63.05%), linear-gradient(60deg, #733fdfff 43%, transparent 43.05%)"
    },
    "livery-76": {
        "background_color": "#0c009f",
        "background_image": "linear-gradient(0deg, #ffe0a8ff 25%, transparent 25.05%), radial-gradient(circle at 67% 79%, #0c009fff 25%, transparent 25.05%), radial-gradient(circle at 50% 78%, #0088caff 50%, transparent 50.05%)"
    },
    "livery-77": {
        "background_color": "#ffffff",
        "background_image": "radial-gradient(circle at 106% 50%, #1dfe00 19%, transparent 19.05%), linear-gradient(-65deg, #ffffffff 50%, transparent 50.05%), linear-gradient(-65deg, #ff0d02ff 60%, transparent 60.05%), linear-gradient(-65deg, #1dfe00 70%, transparent 70.05%)"
    },
    "livery-78": {
        "background_color": "#eeeeeeff",
        "background_image": "linear-gradient(0deg, #eeeeeeff 30%, transparent 30.05%), linear-gradient(0deg, #f21a1fff 35%, transparent 35.05%), linear-gradient(0deg, #eeeeeeff 40%, transparent 40.05%), linear-gradient(0deg, #0060f0ff 45%, transparent 45.05%), linear-gradient(0deg, #eeeeeeff 50%, transparent 50.05%), linear-gradient(0deg, #f21a1fff 55%, transparent 55.05%)"
    },
    "livery-79": {
        "background": "linear-gradient(#fde493 50%, #dd1c17 50%)"
    },
    "livery-80": {
        "background": "linear-gradient(to bottom, rgb(253, 197, 46) 10%, rgb(253, 197, 46) 70%, transparent 70%), linear-gradient(120deg, rgb(253, 197, 46) 45%, rgb(0, 0, 0) 45%)",
        "stroke": "rgb(253, 197, 46)"
    },
    "livery-81": {
        "background_color": "#ffffff",
        "background_image": "radial-gradient(circle at 106% 50%, #b100fe 19%, transparent 19.05%), linear-gradient(-65deg, #ffffffff 50%, transparent 50.05%), linear-gradient(-65deg, #ff0d02ff 60%, transparent 60.05%), linear-gradient(-65deg, #b100fe 70%, transparent 70.05%)"
    },
    "livery-82": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(-65deg, #ffffffff 50%, transparent 50.05%), linear-gradient(-65deg, #ff0d02ff 60%, transparent 60.05%), linear-gradient(-65deg, #0510ffff 70%, transparent 70.05%)"
    },
    "livery-83": {
        "background": "linear-gradient(to bottom, rgb(253, 197, 46) 70%, transparent 70%), linear-gradient(120deg, rgb(0, 0, 0) 40%, rgb(253, 197, 46) 40%, rgb(253, 197, 46) 45%, #ff0d02ff 45%, #ff0d02ff 65%, #ff0d02ff 65%)",
        "stroke": "rgb(253, 197, 46)"
    },
    "livery-84": {
        "background_color": "#ededed",
        "background_image": "linear-gradient(0deg, #ededed 39%, transparent 39.05%), linear-gradient(180deg, #ededed 40%, transparent 40.05%), linear-gradient(-30deg, #ededed 39%, transparent 39.05%), linear-gradient(-30deg, #ff8033ff 42%, transparent 42.05%), linear-gradient(-30deg, #fa3d3dff 45%, transparent 45.05%), linear-gradient(-30deg, #05ce00ff 48%, transparent 48.05%)"
    },
    "livery-85": {
        "background_color": "#ffffff",
        "background_image": "radial-gradient(circle at 100% 0%, #b100feff 19%, transparent 19.05%), linear-gradient(180deg, #ffffffff 75%, transparent 75.05%), linear-gradient(40deg, #b100feff 38%, transparent 38.05%), linear-gradient(40deg, #ffffffff 43%, transparent 43.05%), linear-gradient(0deg, #ff0d02ff 52%, transparent 52.05%)"
    },
    "livery-86": {
        "color": "#fff",
        "fill": "#fff",
        "background": "linear-gradient(#f4a406 33%, #e86628 33% 66%, #5589c3 66%)"
    },
    "livery-87": {
        "background_color": "#e93425",
        "background_image": "linear-gradient(0deg, #a1b3bfff 25%, transparent 25.05%), linear-gradient(180deg, #a1b3bfff 25%, transparent 25.05%)"
    },
    "livery-88": {
        "background_color": "#1e8594",
        "background_image": "linear-gradient(-90deg, #1e8594 30%, transparent 30.05%), linear-gradient(180deg, #1e8594 56%, transparent 56.05%), linear-gradient(90deg, #003642 16%, transparent 16.05%), linear-gradient(205deg, #1e8594 48%, transparent 48.05%), linear-gradient(180deg, #f5eaa5 61%, transparent 61.05%), linear-gradient(213deg, #f5eaa5 50%, transparent 50.05%), linear-gradient(0deg, #003642 50%, transparent 50.05%)"
    },
    "livery-89": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(90deg, #3c94ffff 25%, transparent 25.05%), linear-gradient(270deg, #3c94ffff 25%, transparent 25.05%)"
    },
    "livery-90": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(120deg, #597d35ff 40%, transparent 40.05%), linear-gradient(-60deg, #566d7eff 40%, transparent 40.05%)"
    },
    "livery-91": {
        "background": "linear-gradient(300deg, #8b001d 28%, #0000 28%), linear-gradient(#0000 85%, #ed1d23 85%), linear-gradient(300deg, #0000 31%, #f7941e 31% 39%, #0000 39%), #ed1d23"
    },
    "livery-92": {
        "background_color": "#00EB5A",
        "background_image": "linear-gradient(0deg, rgb(0, 235, 90) 15%, transparent 15.05%), radial-gradient(circle at 50% 35%, rgb(179, 226, 255) 55%, transparent 50.05%), radial-gradient(circle at -19% 50%, rgb(0, 235, 90) 50%, transparent 50.05%)"
    },
    "livery-93": {
        "background": "linear-gradient(to bottom, #dfc760 10%, #dfc760 70%, transparent 70%), linear-gradient(120deg, #dfc760 45%, #7b4d33 45%)",
        "stroke": "#dfc760"
    },
    "livery-94": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(180deg, #ddc7b3ff 30%, transparent 30.05%), linear-gradient(180deg, #aa6f70ff 60%, transparent 60.05%), linear-gradient(0deg, #a81a1dff 40%, transparent 40.05%)"
    },
    "livery-95": {
        "background_color": "#004d1a",
        "background_image": "linear-gradient(60deg, #00c2a4ff 30%, transparent 30.05%)"
    },
    "livery-96": {
        "background_color": "#eabb00",
        "background_image": "linear-gradient(110deg, #c10005ff 45%, transparent 45.05%), linear-gradient(110deg, #eabb00ff 48%, transparent 48.05%), linear-gradient(110deg, #c10005ff 52%, transparent 52.05%)"
    },
    "livery-97": {
        "background_color": "#ea1700"
    },
    "livery-98": {
        "background_color": "#f1b527",
        "background_image": "radial-gradient(circle at 43% 92%, #0000002f 48%, transparent 48.05%), radial-gradient(circle at -1% 98%, #0000002a 55%, transparent 55.05%), radial-gradient(circle at 7% -6%, #00000027 47%, transparent 47.05%), linear-gradient(265deg, #00000022 58%, transparent 58.05%)"
    },
    "livery-99": {
        "background": "linear-gradient(300deg, #0000 72%, #e41e26 20%), linear-gradient(300deg, #6f0f16 28%, #0000 28%), linear-gradient(#0000 85%, #e41e26 85%), linear-gradient(300deg, #0000 31%, #a51e22 31% 39%, #0000 39%), #e41e26"
    },
    "livery-100": {
        "background_color": "#935c1b",
        "background_image": "linear-gradient(90deg, #f5a434ff 33%, transparent 33.05%), linear-gradient(-90deg, #f5a434ff 33%, transparent 33.05%)"
    },
    "livery-101": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(90deg, #ffffffff 35%, transparent 35.05%), linear-gradient(0deg, #ff0000ff 30%, transparent 30.05%), linear-gradient(90deg, #ff0000ff 50%, transparent 50.05%)"
    },
    "livery-102": {
        "background": "linear-gradient(to right, #ff6700 17%, #c8a9bb 17%)"
    },
    "livery-103": {
        "background": "linear-gradient(to right, #ff6700 17%, #ffffff 17%)"
    },
    "livery-104": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(90deg, #fff 14.29%, transparent 14.29%), linear-gradient(90deg, #0084ffff 28.58%, transparent 28.58%), linear-gradient(90deg, #fff 42.87%, transparent 42.87%), linear-gradient(90deg, #0084ffff 57.16%, transparent 57.16%), linear-gradient(90deg, #fff 71.45%, transparent 71.45%), linear-gradient(90deg, #0084ffff 85.74%, transparent 85.74%)"
    },
    "livery-105": {
        "color": "#fff",
        "fill": "#fff",
        "background": "linear-gradient(#08415C 75%, #6B818C 75%)"
    },
    "livery-106": {
        "background": "linear-gradient(120deg, #EC5C96 50%, #312B6B 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-107": {
        "background": "#0055A5",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-108": {
        "background": "radial-gradient(ellipse at -100% 180%, transparent 75%, #f22 75%), radial-gradient(ellipse at -100% 260%, #f22 75%, #fff 75%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#ff2222"
    },
    "livery-109": {
        "background": "linear-gradient(to right, #888888 25%, #122852 25%)"
    },
    "livery-110": {
        "background_color": "#2c0d0b",
        "background_image": "linear-gradient(0deg, #2c0d0bff 33%, transparent 33.05%), linear-gradient(0deg, #cbc7a5ff 66%, transparent 66.05%)"
    },
    "livery-111": {
        "background": "#9F091F",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-112": {
        "background": "linear-gradient(to top, #FE1508 25%, #D5D9DC 25%, #D5D9DC 50%, #FE1508 50%, #FE1508 75%, #D5D9DC 75%)"
    },
    "livery-113": {
        "background": "linear-gradient(to top, #FE1508 50%, #E7D9AE 50%, #E7D9AE 75%, #FE1508 75%)"
    },
    "livery-114": {
        "background": "linear-gradient(to top, #2D3D50 34%, #0B80D7 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-115": {
        "background_color": "#040609",
        "background_image": "radial-gradient(circle at 120% -47%, #040609ff 47%, transparent 47.05%), radial-gradient(circle at 112% -30%, #d43401ff 45%, transparent 45.05%), radial-gradient(circle at 50% 100%, #d43401ff 20%, transparent 20.05%), linear-gradient(270deg, #040609ff 50%, transparent 50.05%), linear-gradient(0deg, #d43401ff 25%, transparent 25.05%)"
    },
    "livery-116": {
        "background_color": "#47dbf9",
        "background_image": "linear-gradient(130deg, #47dbf9ff 15%, transparent 15.05%), linear-gradient(130deg, #e13e9bff 20%, transparent 20.05%), linear-gradient(-50deg, #47dbf9ff 15%, transparent 15.05%), linear-gradient(-50deg, #1555c0ff 20%, transparent 20.05%), linear-gradient(-50deg, #47dbf9ff 25%, transparent 25.05%), linear-gradient(-50deg, #ffffffff 30%, transparent 30.05%)"
    },
    "livery-117": {
        "background": "linear-gradient(to top, #003473 17%, #E20177 17%, #E20177 34%, #ffffff 34%)"
    },
    "livery-118": {
        "background_color": "#24239a",
        "background_image": "linear-gradient(-130deg, #24239aff 32%, transparent 32.05%), linear-gradient(-130deg, #20aae8ff 62%, transparent 62.05%)"
    },
    "livery-119": {
        "background_color": "#2c827f",
        "background_image": "linear-gradient(-180deg, #2c827fff 46%, transparent 46.05%), linear-gradient(-134deg, #c8c32bff 49%, transparent 49.05%), linear-gradient(-180deg, #c8c32bff 74%, transparent 74.05%)"
    },
    "livery-120": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(50deg, #7420cdff 31%, transparent 31.05%), linear-gradient(-130deg, #43e520ff 32%, transparent 32.05%)"
    },
    "livery-121": {
        "background_color": "#20aae8",
        "background_image": "linear-gradient(60deg, #24239aff 24%, transparent 24.05%), linear-gradient(-120deg, #24239aff 36%, transparent 36.05%), linear-gradient(0deg, #20aae8ff 10%, transparent 10.05%), linear-gradient(60deg, #20aae8ff 29%, transparent 29.05%), linear-gradient(60deg, #24239aff 35%, transparent 35.05%)"
    },
    "livery-122": {
        "background_color": "#b93622",
        "background_image": "radial-gradient(circle at 64% 20%, #c6801eff 71%, transparent 71.05%)"
    },
    "livery-123": {
        "background_color": "#24239a",
        "background_image": "radial-gradient(circle at 89% 20%, #24239aff 45%, transparent 45.05%), radial-gradient(circle at 73% -7%, #20aae8ff 67%, transparent 67.05%)"
    },
    "livery-124": {
        "background_color": "#c8c32b",
        "background_image": "linear-gradient(0deg, #2c827fff 30%, transparent 30.05%)"
    },
    "livery-125": {
        "background": "#417082"
    },
    "livery-126": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(90deg, #16007dff 20%, transparent 20.05%), linear-gradient(90deg, #ffffffff 75%, transparent 75.05%), linear-gradient(90deg, #00ce1aff 80%, transparent 80.05%), linear-gradient(90deg, #ffffffff 85%, transparent 85.05%), linear-gradient(90deg, #00ce1aff 90%, transparent 90.05%), linear-gradient(90deg, #ffffffff 95%, transparent 95.05%), linear-gradient(0deg, #9aeda9ff 45%, transparent 45.05%), linear-gradient(0deg, #ffffffff 55%, transparent 55.05%), linear-gradient(0deg, #9aeda9ff 100%, transparent 100.05%)"
    },
    "livery-127": {
        "background_color": "#1b004a",
        "background_image": "linear-gradient(60deg, #000000ff 40%, transparent 40.05%)"
    },
    "livery-128": {
        "background_color": "#000"
    },
    "livery-129": {
        "background": "linear-gradient(to right, #EFCE5A 9%, #C374AE 9%, #C374AE 17%, #048EC8 17%, #048EC8 25%, #4C483D 25%, #4C483D 34%, #000000 34%, #000000 42%, #E41F29 42%, #E41F29 50%, #ED7807 50%, #ED7807 59%, #FCCC10 59%, #FCCC10 67%, #82B648 67%, #82B648 75%, #37A8D5 75%, #37A8D5 84%, #514E9F 84%, #514E9F 92%, #6A46B4 92%)"
    },
    "livery-130": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(112deg, #ffffffff 35%, transparent 35.05%), linear-gradient(112deg, #0411feff 40%, transparent 40.05%), linear-gradient(112deg, #46d9f8ff 45%, transparent 45.05%), radial-gradient(circle at 110% 50%, #46d9f8ff 25%, transparent 25.05%)"
    },
    "livery-131": {
        "background": "conic-gradient(from -90deg at 20% 30%, #2dbbe9 -45deg 135deg, #0000 135deg), conic-gradient(from -90deg at 57% 80%, #fff -45deg 135deg, #0000 135deg), linear-gradient(#fff 0% 45%, #83a603 45% 50%, #0000 50% 100%), linear-gradient(#fff0 0% 70%, #83a60300 70% 85%, #025928 85% 100%), linear-gradient(315deg, #025928 0% 30%, #83a603 30% 35%, #fff0 30% 100%), linear-gradient(#fff0 0% 80%, #83a603 80% 90%, #025928 90% 100%)"
    },
    "livery-132": {
        "background_color": "#f2f209",
        "background_image": "linear-gradient(-30deg, #4ee318ff 50%, transparent 50.05%)"
    },
    "livery-133": {
        "background_color": "#f2f209",
        "background_image": "radial-gradient(circle at 5% 50%, #1518a2ec 27%, transparent 27.05%), linear-gradient(-60deg, #22e018ff 25%, transparent 25.05%), linear-gradient(0deg, #f2f209ff 30%, transparent 30.05%), linear-gradient(-60deg, #f2f209ff 32%, transparent 32.05%), linear-gradient(-60deg, #22e018ff 40%, transparent 40.05%)"
    },
    "livery-134": {
        "background": "linear-gradient(#0000 76%, #dcad1f 76% 80%, #dc241f 80%), radial-gradient(circle at 0 0, #dc241f 25%, #0000 25%), radial-gradient(at 0 0, #f0f0c8 35%, #0000 35%), radial-gradient(circle at 0 20%, #dc241f 35% 40%)"
    },
    "livery-135": {
        "background": "linear-gradient(90deg, #9b2b31 13%, #f6ecb7 13% 63%, #9b2b31 63% 75%, #f6ecb7 75% 88%, #9b2b31 88%)"
    },
    "livery-136": {
        "background_color": "#71552a",
        "background_image": "linear-gradient(0deg, #71552aff 22%, transparent 22.05%), linear-gradient(125deg, #000000ff 34%, transparent 34.05%)"
    },
    "livery-137": {
        "background_color": "#71552a",
        "background_image": "linear-gradient(0deg, #71552aff 22%, transparent 22.05%), linear-gradient(180deg, #000000ff 34%, transparent 34.05%)"
    },
    "livery-138": {
        "background": "linear-gradient(#738183 10%, #fad785 10% 30%, #dc241f 30% 50%, #fad785 50% 70%, #dc241f 70% 90%, #000 90%)"
    },
    "livery-139": {
        "background_color": "#000000",
        "background_image": "radial-gradient(circle at 50% -440%, #fffffffb 90%, transparent 90.05%), radial-gradient(circle at 50% -370%, #f28b00ff 90%, transparent 90.05%)"
    },
    "livery-140": {
        "background_color": "#24196e",
        "background_image": "linear-gradient(120deg, #1e8557ff 35%, transparent 35.05%)"
    },
    "livery-141": {
        "background": "linear-gradient(#c50b0f00 85%, #3d3d3d 85%), radial-gradient(at 0 0, #bc1315 45%, #0000 45%), linear-gradient(90deg, #fff 65%, #0000 65%), radial-gradient(at top, #fff 65%, #bc1315 65%)"
    },
    "livery-142": {
        "background": "#87ceeb"
    },
    "livery-143": {
        "background_color": "#eebe17",
        "background_image": "linear-gradient(0deg, #f20006ff 30%, transparent 30.05%), linear-gradient(0deg, #ffffffff 35%, transparent 35.05%), linear-gradient(0deg, #000000ff 40%, transparent 40.05%)"
    },
    "livery-144": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(0deg, #f20006ff 25%, transparent 25.05%), linear-gradient(68deg, #f20006ff 27%, transparent 27.05%), linear-gradient(0deg, #ffffffff 30%, transparent 30.05%), linear-gradient(68deg, #ffffffff 30%, transparent 30.05%), linear-gradient(0deg, #000000ff 36%, transparent 36.05%), linear-gradient(68deg, #000000ff 33%, transparent 33.05%)"
    },
    "livery-145": {
        "stroke": "#ffbf00",
        "background": "linear-gradient(#ffbf00 50%, #da260e 50% 75%, #ffbf00 75% 80%, #da260e 80%)"
    },
    "livery-146": {
        "background_color": "#a8a8a8",
        "background_image": "radial-gradient(circle at 165% 50%, #0511fdff 50%, transparent 50.05%), linear-gradient(110deg, #a8a8a8ff 30%, transparent 30.05%), linear-gradient(110deg, #0511fdff 40%, transparent 40.05%), linear-gradient(110deg, #ff0d02ff 50%, transparent 50.05%)"
    },
    "livery-147": {
        "background_color": "#a8a8a8",
        "background_image": "radial-gradient(circle at 165% 50%, #1dfe00ff 50%, transparent 50.05%), linear-gradient(110deg, #a8a8a8ff 30%, transparent 30.05%), linear-gradient(110deg, #1dfe00ff 40%, transparent 40.05%), linear-gradient(110deg, #ff0d02ff 50%, transparent 50.05%)"
    },
    "livery-148": {
        "background_color": "#a8a8a8",
        "background_image": "radial-gradient(circle at 165% 50%, #b100feff 50%, transparent 50.05%), linear-gradient(110deg, #a8a8a8ff 30%, transparent 30.05%), linear-gradient(110deg, #b100feff 40%, transparent 40.05%), linear-gradient(110deg, #ff0d02ff 50%, transparent 50.05%)"
    },
    "livery-149": {
        "background_color": "#a8a8a8",
        "background_image": "linear-gradient(110deg, #a8a8a8ff 30%, transparent 30.05%), linear-gradient(110deg, #0511fdff 40%, transparent 40.05%), linear-gradient(110deg, #ff0d02ff 50%, transparent 50.05%)"
    },
    "livery-150": {
        "background": "linear-gradient(to top, #c00000 12%, #FDC52E 12%, #FDC52E 45%, #c00000 45%, #c00000 56%, #FDC52E 56%, #FDC52E 89%, #c00000 89%)",
        "stroke": "#FDC52E"
    },
    "livery-151": {
        "background": "linear-gradient(to top, #91C120 34%, #005CA9 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-152": {
        "background_color": "#a8a8a8",
        "background_image": "radial-gradient(circle at 165% 50%, #0511fdff 50%, transparent 50.05%), linear-gradient(110deg, #a8a8a8ff 30%, transparent 30.05%), linear-gradient(110deg, #0511fdff 40%, transparent 40.05%), linear-gradient(110deg, #1dfe00ff 50%, transparent 50.05%)"
    },
    "livery-153": {
        "background": "linear-gradient(to top, #106032 37%, #FFFFFF 37%, #FFFFFF 46%, #65BC46 46%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-154": {
        "background": "linear-gradient(to left, #504C49 50%, transparent 50%), radial-gradient(circle at center, #504C49 58%, #A3A49F 58%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-155": {
        "background_color": "#a8a8a8",
        "background_image": "radial-gradient(circle at 165% 50%, #0511fdff 50%, transparent 50.05%),\n    linear-gradient(110deg, #a8a8a8ff 30%, transparent 30.05%),\n    linear-gradient(110deg, #0511fdff 40%, transparent 40.05%),\n    linear-gradient(110deg, #ff0d02ff 50%, transparent 50.05%),\n    linear-gradient(0deg, #780088ff 16.6%, transparent 16.6%),\n    linear-gradient(0deg, #004bffff 33.2%, transparent 33.2%),\n    linear-gradient(0deg, #00821aff 49.8%, transparent 49.8%),\n    linear-gradient(0deg, #ffee00ff 66.4%, transparent 66.4%),\n    linear-gradient(0deg, #ff8e01ff 83%, transparent 83%),\n    linear-gradient(0deg, #e60000ff 100%, transparent 100.05%)"
    },
    "livery-156": {
        "background": "linear-gradient(45deg, #ECE9D3 10%, #33732E 10%, #33732E 25%, transparent 25%), linear-gradient(to top, #33732E 30%, #ECE9D3 30%)",
        "stroke": "#ECE9D3"
    },
    "livery-157": {
        "background": "linear-gradient(to top, #122766 34%, #BA2425 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-158": {
        "background": "#051c2c"
    },
    "livery-159": {
        "background": "radial-gradient(at 10% 0%, #fff 62%, #549 62%)",
        "stroke": "#ffffff"
    },
    "livery-160": {
        "background": "linear-gradient(to top, #0074DB 34%, #ECD842 34%)"
    },
    "livery-161": {
        "background_color": "#6b2128",
        "background_image": "linear-gradient(180deg, #eddba5ff 50%, transparent 50.05%)"
    },
    "livery-162": {
        "background_color": "#6b2128",
        "background_image": "linear-gradient(180deg, #eddba5ff 25%, transparent 25.05%), linear-gradient(-180deg, #6b2128ff 50%, transparent 50.05%), linear-gradient(-180deg, #eddba5ff 75%, transparent 75.05%)"
    },
    "livery-163": {
        "background": "linear-gradient(to top, #0E0E0F 34%, #2A4148 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-164": {
        "background_color": "#d20000",
        "background_image": "linear-gradient(0deg, #d20000ff 15%, transparent 15.05%), linear-gradient(0deg, #fbe800ff 65%, transparent 65.05%)"
    },
    "livery-165": {
        "background_color": "#d20000",
        "background_image": "linear-gradient(0deg, #d20000ff 15%, transparent 15.05%), linear-gradient(0deg, #000000ff 25%, transparent 25.05%), linear-gradient(0deg, #fbe800ff 35%, transparent 35.05%)"
    },
    "livery-166": {
        "background": "linear-gradient(to top, #A12D1D 34%, #ECD842 34%)",
        "stroke": "#ECD842"
    },
    "livery-167": {
        "background": "linear-gradient(to top, #004993 25%, #43AC49 25%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-168": {
        "background": "linear-gradient(to top, #29BFCF 20%, transparent 20%), radial-gradient(at top left, #F0F0C8 35%, transparent 35%), linear-gradient(to top, #FFD800 20%, #FFD800 24%, transparent 0%), radial-gradient(circle at 0 20%, #29BFCF 35%, #29BFCF 40%)"
    },
    "livery-169": {
        "background": "linear-gradient(to top, #BBC5C6 34%, #49AF3E 34%, #49AF3E 67%, #298840 67%)"
    },
    "livery-170": {
        "background": "linear-gradient(to top, #324895 20%, #905F35 20%, #905F35 40%, #ffffff 40%)"
    },
    "livery-171": {
        "background": "radial-gradient(circle at -20% 0, #0D2247 48%, #60F3FD 48%, #60F3FD 51%, #0EA0C1 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-172": {
        "background": "linear-gradient(to right, #FCDC4D 67%, #F13D52 67%)"
    },
    "livery-173": {
        "background": "linear-gradient(135deg, #A8B3B5 34%, #404040 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-174": {
        "background": "#A6006B",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-175": {
        "background_color": "#e8e8e8",
        "background_image": "linear-gradient(270deg, #0080ffff 4%, transparent 50.05%)"
    },
    "livery-176": {
        "background": "linear-gradient(to top, #E2DBA5 25%, #D40915 25%, #D40915 75%, #E2DBA5 75%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#D40915"
    },
    "livery-177": {
        "background": "linear-gradient(to right, #6d1d2b 38%, #fff 38%, #fff 50%, #d40915 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#d40915"
    },
    "livery-178": {
        "background": "radial-gradient(circle at -20% 25%, #1F2D6B 48%, #AFAFAF 48%, #AFAFAF 56%, #FFFF 56%, #FFFF 60%, #25B0CF 54%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#25B0CF"
    },
    "livery-179": {
        "background": "linear-gradient(to top, #005633 50%, #71BE43 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-180": {
        "background_color": "#00a83a"
    },
    "livery-181": {
        "background": "linear-gradient(to top, #9CBD64 55%, #FCEB75 55%, #FCEB75 64%, #9CBD64 64%)"
    },
    "livery-182": {
        "background": "#009ADA",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-183": {
        "background_color": "#f00006",
        "background_image": "linear-gradient(-60deg, #2c2c2cff 40%, transparent 40.05%)"
    },
    "livery-184": {
        "stroke": "#ebf1fd",
        "background": "linear-gradient(300deg, #0000 72%, red 20%), linear-gradient(300deg, #004c1e 28%, #0000 28%), linear-gradient(#0000 85%, #ebf1fd 85%), linear-gradient(300deg, #0000 31%, #3f8b4a 31% 39%, #0000 39%), #ebf1fd"
    },
    "livery-185": {
        "background_color": "#0184ef",
        "background_image": "linear-gradient(0deg, #0184efff 33%, transparent 33.05%), linear-gradient(0deg, #ffffffff 66%, transparent 66.05%)"
    },
    "livery-186": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(0deg, #0184efff 10%, transparent 10.05%), linear-gradient(0deg, #f00006ff 20%, transparent 20.05%), linear-gradient(0deg, #feda0eff 90%, transparent 90.05%)"
    },
    "livery-187": {
        "background": "linear-gradient(90deg, #0000 50%, #24a 50%), radial-gradient(ellipse 96% 118% at 60% 50%, transparent 50%, #aaa 50%), radial-gradient(circle at 57% 50%, #24a 55%, #fff 55%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#2244aa"
    },
    "livery-188": {
        "background": "linear-gradient(90deg, #0000 50%, #037 50%), radial-gradient(ellipse 96% 118% at 60% 50%, transparent 50%, #6bf 50%), radial-gradient(circle at 57% 50%, #037 55%, #ff5 55%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#003377"
    },
    "livery-189": {
        "background": "linear-gradient(to left, #bde 20%, #0000 20%), radial-gradient(circle at 71% 79%, #2cf0 63%, #0b1b46 0%), radial-gradient(circle at 74% 80%, #bde 60%, #fff 0%)",
        "stroke": "#bbddee"
    },
    "livery-190": {
        "background": "linear-gradient(to top, #BDCBD8 50%, #53BCE6 50%)"
    },
    "livery-191": {
        "background": "linear-gradient(to top, #FFE7C0 25%, #A11D1D 25%, #A11D1D 75%, #FFE7C0 75%)",
        "color": "#FFE7C0",
        "fill": "#FFE7C0",
        "stroke": "#A11D1D"
    },
    "livery-192": {
        "background": "linear-gradient(to right, #FDEC80 40%, #ECC178 40%, #ECC178 60%, #AD9044 60%, #AD9044 80%, #A30A2F 80%)",
        "color": "#A30A2F",
        "fill": "#A30A2F",
        "stroke": "#FDEC80"
    },
    "livery-193": {
        "background_color": "#49c7fd"
    },
    "livery-194": {
        "background_color": "#ffda46"
    },
    "livery-195": {
        "background": "linear-gradient(110deg, #ED1B23 55%, #ffcf31 55%, #ffcf31 64%, #ffffff 64%, #ffffff 73%, #005da3 73%)",
        "stroke": "#ffffff"
    },
    "livery-196": {
        "background": "#3D90FB"
    },
    "livery-197": {
        "background": "linear-gradient(110deg, #B8BCBB 55%, #1485DD 55%, #1485DD 64%, #ffffff 64%, #ffffff 73%, #076AD9 73%)",
        "stroke": "#B8BCBB"
    },
    "livery-198": {
        "background": "linear-gradient(to top, #6C3641 34%, #F13648 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-199": {
        "background_color": "black"
    },
    "livery-200": {
        "background": "linear-gradient(to right, #FDEC80 15%, #13A7CB 15%, #13A7CB 58%, #ECC178 58%, #ECC178 72%, #AD9044 72%, #AD9044 86%, #A30A2F 86%)"
    },
    "livery-201": {
        "background": "linear-gradient(to top, #FFE7C0 34%, #A11D1D 34%, #A11D1D 67%, #FFE7C0 67%)",
        "color": "#FFE7C0",
        "fill": "#FFE7C0",
        "stroke": "#A11D1D"
    },
    "livery-202": {
        "background": "#A1ACC1"
    },
    "livery-203": {
        "background": "#32ecbc"
    },
    "livery-204": {
        "background": "radial-gradient(circle at 40% 76%, #a8d949 5%, #0000 5%), radial-gradient(circle at 38% 75%, #a8d949 3%, #0000 3%), radial-gradient(circle at 36% 74%, #a8d949 5%, #0000 5%), radial-gradient(circle at 34% 72%, #a8d949 4%, #0000 4%), radial-gradient(circle at 32% 71%, #a8d949 5%, #0000 5%), radial-gradient(circle at 30% 70%, #a8d949 5%, #0000 5%), radial-gradient(circle at 15% 0, #0000 70%, #00652e 70%), linear-gradient(#0000 80%, #a8d949 80%), radial-gradient(circle at -25% 125%, #a8d949 45%, #f9f1ca 45% 50%, #0000 50%), linear-gradient(#30c351 48%, #0000 48%), radial-gradient(circle at 60% 15%, #0000 45%, #f9f1ca 45% 50%, #a8d949 50%), #30c351"
    },
    "livery-205": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(0deg, #8cbdd7ff 50%, transparent 50.05%)"
    },
    "livery-206": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(0deg, #8cbdd7ff 15%, transparent 15.05%)"
    },
    "livery-207": {
        "background_color": "#8cbdd7"
    },
    "livery-208": {
        "background": "linear-gradient(to top, #2765A4 25%, #E5D4C4 25%, #E5D4C4 50%, #2765A4 50%, #2765A4 75%, #E5D4C4 75%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#2765A4"
    },
    "livery-209": {
        "background": "linear-gradient(to top, #193C60 25%, #D4D0A3 25%, #D4D0A3 50%, #193C60 50%, #193C60 75%, #D4D0A3 75%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#193C60"
    },
    "livery-210": {
        "background": "linear-gradient(to top, #1F8CEF 50%, #ffffff 50%)"
    },
    "livery-211": {
        "background": "linear-gradient(to top, #154741 34%, #85DD7F 34%)"
    },
    "livery-212": {
        "background": "linear-gradient(60deg, transparent 60%, #000 60%, #000 65%, transparent 10%), linear-gradient(60deg, transparent 65%, #fff 65%, #fff 72%, transparent 10%), linear-gradient(60deg, transparent 65%, #0063ae 65%), linear-gradient(to top, #ffec00 100%, transparent 10%)",
        "stroke": "#FFEC00"
    },
    "livery-213": {
        "background_color": "#fff"
    },
    "livery-214": {
        "background_color": "#dc241f",
        "background_image": "linear-gradient(0deg, #0977ffff 20%, transparent 20.05%), linear-gradient(0deg, #fbdc00ff 25%, transparent 25.05%)"
    },
    "livery-215": {
        "background": "linear-gradient(to right, rgb(37, 40, 62) 6%, rgb(85, 130, 190) 6%, rgb(85, 130, 190) 12%, rgb(37, 40, 62) 12%, rgb(37, 40, 62) 17%, rgb(219, 149, 75) 17%, rgb(219, 149, 75) 23%, rgb(37, 40, 62) 23%, rgb(37, 40, 62) 28%, rgb(62, 154, 147) 28%, rgb(62, 154, 147) 34%, rgb(37, 40, 62) 34%, rgb(37, 40, 62) 39%, rgb(187, 77, 87) 39%, rgb(187, 77, 87) 45%, rgb(37, 40, 62) 45%, rgb(37, 40, 62) 50%, rgb(213, 149, 81) 50%, rgb(213, 149, 81) 56%, rgb(37, 40, 62) 56%, rgb(37, 40, 62) 67%, rgb(0, 135, 125) 67%, rgb(0, 135, 125) 73%, rgb(213, 149, 81) 73%, rgb(213, 149, 81) 78%, rgb(37, 40, 62) 78%, rgb(37, 40, 62) 84%, rgb(213, 149, 81) 84%, rgb(213, 149, 81) 89%, rgb(37, 40, 62) 89%, rgb(37, 40, 62) 95%, rgb(213, 149, 81) 95%)",
        "__darkreader_inline_bgcolor": "rgba(0, 0, 0, 0)",
        "__darkreader_inline_bgimage": "linear-gradient(to right, #1e2032 6%, #355a8b 6%, #355a8b 12%, #1e2032 12%, #1e2032 17%, #975c1e 17%, #975c1e 23%, #1e2032 23%, #1e2032 28%, #327b76 28%, #327b76 34%, #1e2032 34%, #1e2032 39%, #90373f 39%, #90373f 45%, #1e2032 45%, #1e2032 50%, #915c23 50%, #915c23 56%, #1e2032 56%, #1e2032 67%, #006c64 67%, #006c64 73%, #915c23 73%, #915c23 78%, #1e2032 78%, #1e2032 84%, #915c23 84%, #915c23 89%, #1e2032 89%, #1e2032 95%, #915c23 95%)"
    },
    "livery-216": {
        "background": "linear-gradient(to top, #fff 50%, #83d36c 50%)"
    },
    "livery-217": {
        "background": "linear-gradient(to top, #fff 50%, #e98eaf 50%)"
    },
    "livery-218": {
        "background": "linear-gradient(to top, #AF2529 25%, #FEF389 25%, #FEF389 75%, #AF2529 75%)"
    },
    "livery-219": {
        "background": "linear-gradient(130deg, #005b9a 67%, #0a4595 67%, #0a4595 84%, #005b9a 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-220": {
        "background": "linear-gradient(60deg, #0f264f 30%, #0000 30%), repeating-conic-gradient(from 330deg at 34.6% 82%, #0d4485 0deg 61deg, #105191 61deg 87deg, #1e6fa7 77deg 180deg)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#1e6fa7"
    },
    "livery-221": {
        "background": "linear-gradient(300deg, #081 28%, #0000 28%), linear-gradient(to top, #fd0 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #3b0 31%, #3b0 39%, #0000 39%), linear-gradient(to top, #fd0 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #3b0 20%), #fd0",
        "stroke": "#ffdd00"
    },
    "livery-222": {
        "background": "linear-gradient(60deg, #005049 30%, #0000 30%), repeating-conic-gradient(from 330deg at 34.6% 82%, #0a955a 0deg 61deg, #5eab2b 61deg 87deg, #84c350 77deg 180deg)",
        "stroke": "#84c350"
    },
    "livery-223": {
        "background": "linear-gradient(300deg, #1e1071 28%, #0000 28%), linear-gradient(to top, #634aca 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #7172f1 31%, #7172f1 39%, #0000 39%), #634aca",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-224": {
        "background": "linear-gradient(135deg, #a8c542 25%, #2d2d2c 25%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-225": {
        "background": "linear-gradient(to left, #000 50%, transparent 50%), radial-gradient(circle at center, #000 58%, #e5e0ba 58%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-226": {
        "background": "radial-gradient(circle at 55% 25%, rgb(255, 255, 255) 8%, rgba(0, 0, 0, 0) 8%), radial-gradient(circle at 55% center, rgb(255, 255, 255) 8%, rgba(0, 0, 0, 0) 8%), radial-gradient(circle at 55% 75%, rgb(255, 255, 255) 8%, rgba(0, 0, 0, 0) 8%), linear-gradient(90deg, rgb(251, 55, 62) 10%, rgb(255, 255, 255) 10%, rgb(255, 255, 255) 46%, rgb(251, 55, 62) 46%, rgb(251, 55, 62) 64%, rgb(255, 255, 255) 64%, rgb(255, 255, 255) 91%, rgb(251, 55, 62) 91%)",
        "__darkreader_inline_bgcolor": "rgba(0, 0, 0, 0)",
        "__darkreader_inline_bgimage": "radial-gradient(circle at 55% 25%, #181a1b 8%, rgba(0, 0, 0, 0) 8%), radial-gradient(circle at 55% center, #181a1b 8%, rgba(0, 0, 0, 0) 8%), radial-gradient(circle at 55% 75%, #181a1b 8%, rgba(0, 0, 0, 0) 8%), linear-gradient(90deg, #aa0309 10%, #181a1b 10%, #181a1b 46%, #aa0309 46%, #aa0309 64%, #181a1b 64%, #181a1b 91%, #aa0309 91%)"
    },
    "livery-227": {
        "background_color": "#7e7e7e",
        "background_image": "linear-gradient(0deg, #001226 25%, transparent 25.05%), radial-gradient(circle at 57% 25%, #7e7e7e 45%, transparent 30.05%), linear-gradient(-90deg, #001226 50%, transparent 50.05%), linear-gradient(138deg, #3e9ffe 16%, transparent 16.05%)"
    },
    "livery-228": {
        "background": "linear-gradient(60deg, #101417 30%, #0000 30%), repeating-conic-gradient(from 330deg at 34.6% 82%, #2d8dc0 0deg 5deg, #417f32 5deg 10deg, #414550 10deg 61deg, #585c5f 61deg 87deg, #8d9192 77deg 180deg)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-229": {
        "background_color": "#7e7e7e",
        "background_image": "linear-gradient(0deg, #001226 25%, transparent 25.05%), radial-gradient(circle at 57% 25%, #7e7e7e 45%, transparent 30.05%), linear-gradient(-90deg, #001226 50%, transparent 50.05%)"
    },
    "livery-230": {
        "background": "radial-gradient(circle at 100% 10%, #004C98 20%, transparent 20%), radial-gradient(circle at 76% 61%, transparent 50%, #FEDC00 50%), radial-gradient(circle at 100% 60%, #004C98 50%, #00ADEF 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#004C98"
    },
    "livery-231": {
        "background_color": "#000000",
        "background_image": "linear-gradient(180deg, #0055fffb 9%, transparent 9.05%), linear-gradient(0deg, #0040ffff 35%, transparent 35.05%), linear-gradient(0deg, #ffffffff 38%, transparent 38.05%), linear-gradient(0deg, #00ccffff 44%, transparent 44.05%), linear-gradient(-37deg, #0040ffff 33%, transparent 33.05%), linear-gradient(-37deg, #00d7ffff 39%, transparent 39.05%)"
    },
    "livery-232": {
        "background": "radial-gradient(circle at 100% 10%, #004C98 20%, transparent 20%), radial-gradient(circle at 76% 61%, transparent 50%, #c9cdd0 50%), radial-gradient(circle at 100% 60%, #004C98 50%, #00ADEF 50%)",
        "stroke": "#c9cdd0"
    },
    "livery-233": {
        "background": "radial-gradient(ellipse 133% 138% at 5% 28%, #0000 60%, #37b 60%), radial-gradient(ellipse 130% 133% at 0% 23%, #0000 60%, #fa3 60%), #e23",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#ee2233"
    },
    "livery-234": {
        "background_color": "#323232",
        "background_image": "radial-gradient(circle at 67% 140%, #3fb0ffff 50%, transparent 50.05%),radial-gradient(circle at 67% 142%, #d9d4dcff 52%, transparent 52.05%)"
    },
    "livery-235": {
        "background": "linear-gradient(to top, #00dc35 34%, #ffffff 34%)"
    },
    "livery-236": {
        "background": "linear-gradient(135deg, #FB0000 20%, #FFBE00 20%, #FFBE00 35%, #FB0000 35%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-237": {
        "background_color": "#ffbb00",
        "background_image": "linear-gradient(-90deg, #000000ff 10%, transparent 110.05%)"
    },
    "livery-238": {
        "background": "radial-gradient(circle at right, #b4007b 65%, #ca6197 65%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-239": {
        "background_color": "#7e7e7e",
        "background_image": "linear-gradient(0deg, #001226 25%, transparent 25.05%), radial-gradient(circle at 57% 25%, #7e7e7e 45%, transparent 30.05%), linear-gradient(-90deg, #001226 50%, transparent 50.05%), linear-gradient(138deg, #84bf2f 16%, transparent 16.05%)"
    },
    "livery-240": {
        "background_color": "#7e7e7e",
        "background_image": "linear-gradient(0deg, #001226 25%, transparent 25.05%), radial-gradient(circle at 57% 25%, #7e7e7e 45%, transparent 30.05%), linear-gradient(-90deg, #001226 50%, transparent 50.05%), linear-gradient(138deg, #fe3fff 16%, transparent 16.05%)"
    },
    "livery-241": {
        "background_color": "#7e7e7e",
        "background_image": "linear-gradient(0deg, #001226 25%, transparent 25.05%), radial-gradient(circle at 57% 25%, #7e7e7e 45%, transparent 30.05%), linear-gradient(-90deg, #001226 50%, transparent 50.05%), linear-gradient(138deg, #be0000 16%, transparent 16.05%)"
    },
    "livery-242": {
        "background_color": "#7e7e7e",
        "background_image": "linear-gradient(0deg, #001226 25%, transparent 25.05%), radial-gradient(circle at 57% 25%, #7e7e7e 45%, transparent 30.05%), linear-gradient(-90deg, #001226 50%, transparent 50.05%), linear-gradient(138deg, #ff9f40 16%, transparent 16.05%)"
    },
    "livery-243": {
        "background": "linear-gradient(300deg, #26a 28%, #0000 28%), linear-gradient(to top, #2bf 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #6df 31%, #6df 39%, #0000 39%), linear-gradient(to top, #2bf 60%, #2bf 60%)",
        "stroke": "#22bbff"
    },
    "livery-244": {
        "background_color": "#ff9f40",
        "background_image": "radial-gradient(circle at -30% 50%, #134c17ff 50%, transparent 50.05%)"
    },
    "livery-245": {
        "background": "linear-gradient(to top, #006e63 25%, #e9dd5b 25%)"
    },
    "livery-246": {
        "background_color": "#7f7f7f",
        "background_image": "linear-gradient(0deg, #00497eff 15%, transparent 15.05%),linear-gradient(0deg, #00233dff 30%, transparent 30.05%),linear-gradient(-30deg, #7f7f7fff 50%, transparent 50.05%),linear-gradient(0deg, #7f7f7fff 55%, transparent 55.05%),linear-gradient(0deg, #c0bf8fff 65%, transparent 65.05%),linear-gradient(-30deg, #c0bf8fff 55%, transparent 55.05%)"
    },
    "livery-247": {
        "background": "linear-gradient(to top, #734778 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #d4bfe9 60%, #d4bfe9 70%, #a08cbd 70%)"
    },
    "livery-248": {
        "background_color": "#7f7f7f",
        "background_image": "linear-gradient(0deg, #00233dff 15%, transparent 15.05%),linear-gradient(0deg, #7f7f7fff 25%, transparent 25.05%),linear-gradient(0deg, #00233dff 35%, transparent 35.05%),linear-gradient(0deg, #7f7f7fff 50%, transparent 50.05%),linear-gradient(0deg, #00497eff 55%, transparent 55.05%),linear-gradient(0deg, #bfbebfff 65%, transparent 65.05%),linear-gradient(0deg, #00497eff 70%, transparent 70.05%)"
    },
    "livery-249": {
        "background": "linear-gradient(to top, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-250": {
        "background": "linear-gradient(to top, #0093d8 50%, #32bcee 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-251": {
        "background": "linear-gradient(120deg, #32bcee 45%, #ffff 45%)"
    },
    "livery-252": {
        "background": "linear-gradient(to top, #d1312a 28%, #eae0c4 28%, #eae0c4 50%, #d1312a 50%, #d1312a 56%, #eae0c4 56%, #eae0c4 78%, #d1312a 78%)",
        "stroke": "#eae0c4"
    },
    "livery-253": {
        "background_color": "#333333",
        "background_image": "linear-gradient(70deg, #3fb0ffff 40%, transparent 40.05%)"
    },
    "livery-254": {
        "background": "linear-gradient(to right, #0988d5 50%, #7ec22a 50%, #7ec22a 63%, #3d9d11 63%, #3d9d11 75%, #003227 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-255": {
        "background_color": "#333333",
        "background_image": "linear-gradient(70deg, #ff9f40 40%, transparent 40.05%)"
    },
    "livery-256": {
        "background_color": "#333333",
        "background_image": "linear-gradient(70deg, #ff3e3f 40%, transparent 40.05%)"
    },
    "livery-257": {
        "background_color": "#333333",
        "background_image": "linear-gradient(70deg, #666666 40%, transparent 40.05%)"
    },
    "livery-258": {
        "background_color": "#bfbebf",
        "background_image": "radial-gradient(circle at -10% -10%, #00233dff 50%, transparent 50.05%),radial-gradient(circle at -7% -5%, #7dbfa3ff 48%, transparent 56.05%)"
    },
    "livery-259": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(0deg, rgb(48, 48, 48) 15%, transparent 15.05%),linear-gradient(0deg, rgb(91, 73, 108) 30%, transparent 30.05%),linear-gradient(65deg, rgb(91, 73, 108) 21%, transparent 21.05%),linear-gradient(0deg, rgb(196, 48, 48) 35%, transparent 35.05%),linear-gradient(64deg, rgb(196, 48, 48) 25%, transparent 25.05%),linear-gradient(0deg, rgb(91, 73, 108) 40%, transparent 40.05%),linear-gradient(64deg, rgb(91, 73, 108) 28%, transparent 28.05%)"
    },
    "livery-260": {
        "background_color": "#ff0000",
        "background_image": "linear-gradient(180deg, #0000ffff 25%, transparent 25.05%)"
    },
    "livery-261": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(0deg, #0049b7ff 20%, transparent 20.05%),linear-gradient(65deg, #0049b7ff 30%, transparent 30.05%),linear-gradient(0deg, #ffd900ff 25%, transparent 25.05%),linear-gradient(65deg, #ffd900ff 33%, transparent 33.05%),linear-gradient(0deg, #0049b7ff 31%, transparent 31.05%),linear-gradient(65deg, #0049b7ff 36%, transparent 36.05%)"
    },
    "livery-262": {
        "background": "#DC241F",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-263": {
        "background": "linear-gradient(to top, #2d3677 34%, #66aafd 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-264": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(-45deg, #464646ff 45%, transparent 45.05%),linear-gradient(-45deg, #a90707ff 55%, transparent 55.05%)"
    },
    "livery-265": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(-45deg, #464646ff  40%, transparent 40.05%),linear-gradient(-45deg, #1db002ff 45%, transparent 45.05%),linear-gradient(-45deg, #a90707ff 55%, transparent 55.05%)"
    },
    "livery-266": {
        "background_color": "#22a9ea",
        "background_image": "linear-gradient(20deg, #000000ff 30%, transparent 30.05%)"
    },
    "livery-267": {
        "background_color": "#ffffff",
        "background_image": "radial-gradient(circle at -0% 150%, #00adcc 50%, transparent 50.05%),radial-gradient(circle at 57% 19%, #fff 55%, transparent 55.05%),radial-gradient(circle at 110% 153%, #5271ff 50%, transparent 50.05%)"
    },
    "livery-268": {
        "background": "linear-gradient(to right, #E30315 50%, #074787 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-269": {
        "background": "linear-gradient(to top, #508352 84%, #e2fa83 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-270": {
        "background": "repeating-conic-gradient(from 259deg at 50% 91%, rgb(238, 0, 17) 0deg, rgb(238, 0, 17) 71deg, rgb(255, 238, 0) 71deg, rgb(255, 238, 0) 128deg, rgb(153, 17, 17) 128deg, rgb(153, 17, 17) 137deg, rgb(238, 102, 0) 137deg, rgb(238, 102, 0) 146deg, rgb(238, 0, 17) 0deg, rgb(238, 0, 17) 360deg)",
        "__darkreader_inline_bgcolor": "rgba(0, 0, 0, 0)",
        "__darkreader_inline_bgimage": "repeating-conic-gradient(from 259deg at 50% 91%, #be000e 0deg, #be000e 71deg, #998f00 71deg, #998f00 128deg, #7a0e0e 128deg, #7a0e0e 137deg, #be5200 137deg, #be5200 146deg, #be000e 0deg, #be000e 360deg)"
    },
    "livery-271": {
        "background": "#0E4194",
        "color": "#FFD908",
        "fill": "#FFD908"
    },
    "livery-272": {
        "background_color": "#bd0625",
        "background_image": "radial-gradient(circle at 88% 89%, #ffd701ff 7%, transparent 7.05%),radial-gradient(circle at 19% 25%, #078c00ff 10%, transparent 10.05%),radial-gradient(circle at 9% 73%, #ffd701ff 7%, transparent 7.05%),radial-gradient(circle at 46% 73%, #078c00ff 5%, transparent 5.05%),radial-gradient(circle at 41% 9%, #ffd701ff 6%, transparent 6.05%),radial-gradient(circle at 67% 14%, #078c00ff 4%, transparent 4.05%),radial-gradient(circle at 67% 46%, #ffd701ff 7%, transparent 7.05%),radial-gradient(circle at 85% 51%, #078c00ff 5%, transparent 5.05%)"
    },
    "livery-273": {
        "background_color": "#078c00",
        "background_image": "radial-gradient(circle at 88% 89%, #ffd701ff 7%, transparent 7.05%),radial-gradient(circle at 19% 25%, #bd0625ff 10%, transparent 10.05%),radial-gradient(circle at 9% 73%, #ffd701ff 7%, transparent 7.05%),radial-gradient(circle at 46% 73%, #bd0625ff 5%, transparent 5.05%),radial-gradient(circle at 41% 9%, #ffd701ff 6%, transparent 6.05%),radial-gradient(circle at 67% 14%, #bd0625ff 4%, transparent 4.05%),radial-gradient(circle at 67% 46%, #ffd701ff 7%, transparent 7.05%),radial-gradient(circle at 85% 51%, #bd0625ff 5%, transparent 5.05%)"
    },
    "livery-274": {
        "background_color": "#078c00",
        "background_image": "linear-gradient(90deg, #bd0625ff 45%, transparent 45.05%),linear-gradient(-90deg, #bd0625ff 45%, transparent 45.05%)"
    },
    "livery-275": {
        "background": "linear-gradient(60deg, transparent 65%, #fff 65%, #fff 70%, transparent 70%), linear-gradient(110deg, transparent 70%, #003268 70%), linear-gradient(60deg, transparent 65%, #0095d9 65%), linear-gradient(to top, #eed878 20%, #cba85f 20%)",
        "stroke": "#eed878"
    },
    "livery-276": {
        "background_color": "#004d89",
        "background_image": "linear-gradient(0deg, #0aa2c1ff 20%, transparent 20.05%),linear-gradient(0deg, #0084d5ff 40%, transparent 40.05%)"
    },
    "livery-277": {
        "background": "radial-gradient(circle at top left, transparent 67%, #60BB46 67%, #60BB46 70%, #00652E 70%), radial-gradient(circle at 5% -30%, #60BB46 65%, transparent 65%), linear-gradient(to left, #FFF101 15%, #FFF101 15%, #65BC46 85%)",
        "stroke": "#60BB46"
    },
    "livery-278": {
        "background": "linear-gradient(#0000 80%,#1f3d71 80%),radial-gradient(circle at 0 0,#0000 70%,#f6e732 70% 80%,#19376f 80%),radial-gradient(circle at 100% 100%,#0e4194 90%,#f6e72d 90% 95%,#0e4194 95%)"
    },
    "livery-279": {
        "background": "linear-gradient(to top, #7a7a78 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-280": {
        "background": "linear-gradient(to top, #8079a5 34%, #95d3de 34%)"
    },
    "livery-281": {
        "background": "linear-gradient(120deg, #e30514 45%, #ffff 45%)",
        "stroke": "#ffffff"
    },
    "livery-282": {
        "background": "linear-gradient(to top, #9F0F06 50%, #C50B0F 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-283": {
        "background_color": "#9800ff",
        "background_image": "linear-gradient(110deg, #9800ffff 35%, transparent 35.05%),linear-gradient(180deg, #040404ff 25%, transparent 25.05%),linear-gradient(0deg, #000000ff 25%, transparent 25.05%),linear-gradient(-70deg, #000000ff 30%, transparent 30.05%)"
    },
    "livery-284": {
        "background": "linear-gradient(to top, #0b2510 50%, #0d4b23 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-285": {
        "background": "linear-gradient(to top, #43e8a4 25%, #fafaf8 25%, #fafaf8 50%, #fde92e 50%, #fde92e 75%, #fafaf8 75%)"
    },
    "livery-286": {
        "background_color": "#000000",
        "background_image": "linear-gradient(-70deg, #9800ffff 20%, transparent 20.05%),linear-gradient(-70deg, #000000ff 27%, transparent 27.05%),linear-gradient(-70deg, #9800ffff 35%, transparent 35.05%)"
    },
    "livery-287": {
        "background": "linear-gradient(300deg, #004c1e 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #3f8b4a 31%, #3f8b4a 39%, #0000 39%), linear-gradient(to top, #ebf1fd 100%, #0000 60%), linear-gradient(300deg, #0000 80%, #f00 20%)",
        "stroke": "#EBF1FD"
    },
    "livery-288": {
        "background": "rgb(121, 163, 193)",
        "__darkreader_inline_bgcolor": "#355973",
        "__darkreader_inline_bgimage": "none"
    },
    "livery-289": {
        "background_color": "#000000",
        "background_image": "linear-gradient(-66deg, #000000ff 37%, transparent 37.05%),linear-gradient(0deg, #9800ffff 37%, transparent 37.05%),linear-gradient(-67deg, #9800ffff 67%, transparent 67.05%)"
    },
    "livery-290": {
        "background": "linear-gradient(to top, #3d9851 40%, #fbf9ea 40%, #fbf9ea 60%, #3d9851 60%)"
    },
    "livery-291": {
        "background": "linear-gradient(300deg, #000 28%, #0000 28%), linear-gradient(to top, #ffb300 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #000 31%, #000 39%, #0000 39%), #ffb300",
        "stroke": "#EBF1FD"
    },
    "livery-292": {
        "background": "linear-gradient(to top, #e5dcc8 50%, #934c49 50%)",
        "stroke": "#e5dcc8"
    },
    "livery-293": {
        "background": "radial-gradient(ellipse 85% 60% at 57% 100%, #0025aa 30%, #ffffff 30%, #ffffff 32%, transparent 32%), radial-gradient(ellipse 70% 100% at 105% 90%, #0025aa 30%, #ffffff 30%, #ffffff 32%, #9c7944 32%, #9c7944 36%, transparent 36%), radial-gradient(ellipse 85% 60% at 57% 100%, #0025aa 30%, #ffffff 30%, #ffffff 32%, #9c7944 32%, #9c7944 38%, #ffffff 38%)",
        "stroke": "#ffffff"
    },
    "livery-294": {
        "background": "linear-gradient(to top, #25489a 25%, #7ecef1 25%)"
    },
    "livery-295": {
        "background_color": "black",
        "background_image": "radial-gradient(circle at 34% 25%, #000000ff 8%, transparent 8.05%), radial-gradient(circle at 68% 25%, #000000ff 8%, transparent 8.05%), linear-gradient(0deg, #ffffffff 10%, transparent 41.05%), url('your-original-photo.jpg')",
        ".spiky_mouth {position": "absolute",
        "width": "150px",
        "height": "150px",
        "clip_path": "polygon(50% 0%, 60% 30%, 100% 35%, 65% 55%, 75% 100%, 50% 75%, 25% 100%, 35% 55%, 0% 35%, 40% 30%)",
        "bottom": "50px",
        "left": "50%",
        "transform": "translateX(-50%)"
    },
    "livery-296": {
        "background": "linear-gradient(300deg, #57a 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #ebf1fd",
        "stroke": "#EBF1FD"
    },
    "livery-297": {
        "background": "linear-gradient(135deg, #199ED4 34%, #013E83 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-298": {
        "background_color": "black",
        "background_image": "radial-gradient(circle at 34% 25%,#000000ff 8%,transparent 8.05%),radial-gradient(circle at 68% 25%,#000000ff 8%,transparent 8.05%),linear-gradient(0deg,#ffffff 10%,transparent 41.05%),url('your-original-photo.jpg')",
        ".spiky_mouth{position": "absolute",
        "width": "150px",
        "height": "150px",
        "clip_path": "polygon(50% 0%,60% 30%,100% 35%,65% 55%,75% 100%,50% 75%,25% 100%,35% 55%,0% 35%,40% 30%)",
        "bottom": "50px",
        "left": "50%",
        "transform": "translateX(-50%)"
    },
    "livery-299": {
        "background": "linear-gradient(135deg, #0154A3 40%, #1A2C49 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-300": {
        "background": "linear-gradient(135deg, #e30712 34%, #000 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-301": {
        "background": "linear-gradient(135deg, #C70C10 40%, #771613 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-302": {
        "background": "linear-gradient(135deg, #EF3237 40%, #B41B2B 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-303": {
        "background": "linear-gradient(135deg, #E6772F 40%, #B82F2D 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-304": {
        "background": "radial-gradient(circle at 40% 76%, #A8D949 5%, transparent 5%), radial-gradient(circle at 38% 75%, #A8D949 3%, transparent 3%), radial-gradient(circle at 36% 74%, #A8D949 5%, transparent 5%), radial-gradient(circle at 34% 72%, #A8D949 4%, transparent 4%), radial-gradient(circle at 32% 71%, #A8D949 5%, transparent 5%), radial-gradient(circle at 30% 70%, #A8D949 5%, transparent 5%), radial-gradient(circle at 15% 0%, transparent 70%, #00652E 70%), linear-gradient(to top, #A8D949 20%, transparent 20%), radial-gradient(circle at -25% 125%, #A8D949 45%, #F9F1CA 45%, #F9F1CA 50%, transparent 50%), linear-gradient(to top, transparent 52%, #30C351 52%), radial-gradient(circle at 60% 15%, transparent 45%, #F9F1CA 45%, #F9F1CA 50%, #A8D949 50%), #30C351"
    },
    "livery-305": {
        "background": "linear-gradient(300deg, #0000 72%, #ed1d23 20%), linear-gradient(300deg, #8b001d 28%, #0000 28%), linear-gradient(to top, #ed1d23 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #f7941e 31%, #f7941e 39%, #0000 39%), #ed1d23",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#ed1d23"
    },
    "livery-306": {
        "background": "radial-gradient(circle at 72% 35%,#0b6c5f 42%,#83cfc6 42%)"
    },
    "livery-307": {
        "background_color": "#212834",
        "background_image": "linear-gradient(0deg, #384b64ff 25%, transparent 25.05%),radial-gradient(circle at 39% -6%, #212834ff 61%, transparent 61.05%),radial-gradient(circle at 50% 10%, #324257ff 63%, transparent 63.05%),radial-gradient(circle at 108% 108%, #384b64ff 56%, transparent 56.05%)"
    },
    "livery-308": {
        "background": "linear-gradient(300deg, #0000 72%, #eae065 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #ebf1fd"
    },
    "livery-309": {
        "background": "linear-gradient(300deg, #0000 72%, #c50004 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-310": {
        "background": "linear-gradient(300deg, #0000 72%, #186ed5 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-311": {
        "background": "linear-gradient(300deg, #0000 72%, #a4f5ee 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-312": {
        "background": "linear-gradient(300deg, #0000 72%, #50caf2 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-313": {
        "background": "linear-gradient(to top, #d6e5ec 25%, #c43b29 25%, #c43b29 50%, #d6e5ec 50%, #d6e5ec 75%, #c43b29 75%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#c43b29"
    },
    "livery-314": {
        "background": "#df4f84",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-315": {
        "background": "linear-gradient(135deg, #fff 34%, #ff9a01 34%, #ff9a01 50%, #d6061c 50%)"
    },
    "livery-316": {
        "background_color": "#442f34",
        "background_image": "linear-gradient(0deg, #553a40ff 25%, transparent 25.05%),radial-gradient(circle at 39% -6%, #442f34ff 61%, transparent 61.05%),radial-gradient(circle at 50% 10%, #4a2f36ff 63%, transparent 63.05%),radial-gradient(circle at 108% 108%, #553a40ff 56%, transparent 56.05%)"
    },
    "livery-317": {
        "background": "linear-gradient(to right, #ed7310 75%, #141414 75%, #141414 88%, #ed7310 88%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-318": {
        "background": "radial-gradient(circle at -30% 25%, #25B0CF 48%, #c4db81 48%, #c4db81 56%, #FFFF 56%, #FFFF 62%, #25B0CF 56%)",
        "stroke": "#25b0cf"
    },
    "livery-319": {
        "background": "radial-gradient(circle at -50% 25%, #25B0CF 48%, #6e3697 48%, #6e3697 52%, #3c75d1 52%, #3c75d1 56%, #67b643 56%, #67b643 60%, #e2c430 60%, #e2c430 64%, #ec9629 64%, #ec9629 68%, #db3a31 68%, #db3a31 72%, #25B0CF 66%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-320": {
        "background": "radial-gradient(circle at -30% 25%, #A5D668 48%, #2BBE3C 48%, #2BBE3C 54%, #01A175 54%, #01A175 60%, #008286 60%, #008286 66%, #0F4A7C 56%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-321": {
        "background_color": "#ffffff",
        "background_image": "radial-gradient(circle at -0% 150%, #c00 50%, transparent 50.05%),radial-gradient(circle at 57% 19%, #fff 55%, transparent 55.05%),radial-gradient(circle at 110% 153%, #ff5252 50%, transparent 50.05%)"
    },
    "livery-322": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(0deg, rgb(91, 73, 108) 15%, transparent 15.05%),linear-gradient(0deg, rgb(91, 73, 108) 30%, transparent 30.05%),linear-gradient(65deg, rgb(91, 73, 108) 21%, transparent 21.05%),linear-gradient(0deg, rgb(196, 48, 48) 35%, transparent 35.05%),linear-gradient(64deg, rgb(196, 48, 48) 25%, transparent 25.05%),linear-gradient(0deg, rgb(91, 73, 108) 40%, transparent 40.05%),linear-gradient(64deg, rgb(91, 73, 108) 28%, transparent 28.05%)"
    },
    "livery-323": {
        "background": "linear-gradient(100deg, #A2DC4B 40%, #ffffff 40%, #ffffff 60%, #925BA5 60%)"
    },
    "livery-324": {
        "background": "linear-gradient(to top, #0025aa 34%, #ffffff 34%)",
        "stroke": "#ffffff"
    },
    "livery-325": {
        "background": "linear-gradient(to right, #ffff02 67%, #4262a5 67%)"
    },
    "livery-326": {
        "background_color": "#9ed5fc",
        "background_image": "linear-gradient(70deg, #020088ff 25%, transparent 25.05%),linear-gradient(-70deg, #020088ff 25%, transparent 25.05%),linear-gradient(110deg, #0496fdff 30%, transparent 30.05%),linear-gradient(-110deg, #0496fdff 30%, transparent 30.05%)"
    },
    "livery-327": {
        "background": "linear-gradient(110deg, #ff6700 55%, #fff 55%, #fff 62%, #2b2b8d 62%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#2B2B8D"
    },
    "livery-328": {
        "background": "linear-gradient(248deg, #222222 30%, #dd0c15 30%, #dd0c15 34%, #222222 34%, #222222 38%, #dd0c15 38%, #dd0c15 41%, #222222 41%, #222222 45%, #dd0c15 45%, #dd0c15 49%, #222222 49%, #222222 52%, #dd0c15 52%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-329": {
        "background": "rgb(67, 69, 70)",
        "__darkreader_inline_bgcolor": "#34383a",
        "__darkreader_inline_bgimage": "none"
    },
    "livery-330": {
        "background": "rgb(49, 148, 30)",
        "__darkreader_inline_bgcolor": "#277618",
        "__darkreader_inline_bgimage": "none"
    },
    "livery-331": {
        "background": "radial-gradient(circle at -20% 25%, #9a9da2 56%, #0eacd0 56%, #090f25 85%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-332": {
        "background": "radial-gradient(circle at -20% 25%, #5a6c9f 56%, #0eacd0 56%, #090f25 85%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-333": {
        "background": "linear-gradient(135deg, #860f12 25%, #fd1b0b 25%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-334": {
        "background": "linear-gradient(to right, rgb(189, 0, 0) 17%, rgb(0, 191, 67) 17%, rgb(0, 191, 67) 50%, rgb(227, 88, 142) 50%, rgb(227, 88, 142) 84%, rgb(227, 76, 42) 84%)",
        "__darkreader_inline_bgcolor": "rgba(0, 0, 0, 0)",
        "__darkreader_inline_bgimage": "linear-gradient(to right, #970000 17%, #009936 17%, #009936 50%, #901847 50%, #901847 84%, #ad3217 84%)"
    },
    "livery-335": {
        "background": "radial-gradient(ellipse at 23% 140%, #ff2222 31%, transparent 31%), radial-gradient(circle at 51% 42%, #ffffcb 49%, transparent 0%), linear-gradient(109deg, #ffffcb 1%, #ffffcb 46%, transparent 10%), linear-gradient(3deg, #f22 20%, #0000 20%), radial-gradient(circle at 45% 24%, #aacc88 60%, transparent 10%), linear-gradient(to top, #f22 20%, #f22 20%)",
        "stroke": "#ffffcb"
    },
    "livery-336": {
        "background": "radial-gradient(ellipse at 23% 140%, #ff2222 31%, transparent 31%), radial-gradient(circle at 51% 42%, #ffffcb 49%, transparent 0%), linear-gradient(109deg, #ffffcb 1%, #ffffcb 46%, transparent 10%), linear-gradient(3deg, #f22 20%, #0000 20%), radial-gradient(circle at 45% 24%, #554488 60%, transparent 10%), linear-gradient(to top, #f22 20%, #f22 20%)",
        "stroke": "#ffffcb"
    },
    "livery-337": {
        "background": "rgb(51, 37, 86)",
        "__darkreader_inline_bgcolor": "#291e45",
        "__darkreader_inline_bgimage": "none"
    },
    "livery-338": {
        "background": "linear-gradient(#0000 80%,#0f6db4 80%),radial-gradient(circle at 0 0,#0000 60%,#fff 60% 70%,#fcc201 70%),radial-gradient(circle at bottom,#0061ae 84%,#fff 84% 92%,#fcc201 92%)"
    },
    "livery-339": {
        "background": "linear-gradient(to right, #e2ded5 60%, #d25d58 60%, #d25d58 80%, #2b3789 80%)"
    },
    "livery-340": {
        "background": "radial-gradient(circle at 1% 50%, #f92 35%, #fff0 35%), radial-gradient(circle at 8% 46%, #ecba41 37%, #fff0 37%), radial-gradient(circle at 12% 42%, #1bb 40%, #066 40%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#00665f"
    },
    "livery-341": {
        "background_color": "#000000",
        "background_image": "linear-gradient(-90deg, #ff0000ff 53%, transparent 53.05%),linear-gradient(-90deg, #ffffffff 58%, transparent 58.05%),linear-gradient(111deg, #ff428476 50%, transparent 50.05%)"
    },
    "livery-342": {
        "background": "#002664",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-343": {
        "background": "linear-gradient(to top, #ae3518 25%, #dfd6b5 25%, #dfd6b5 75%, #ae3518 75%)"
    },
    "livery-344": {
        "background": "radial-gradient(circle at -20% 25%, #25B0CF 48%, #0075e9 48%, #0075e9 56%, #FFFF 56%, #FFFF 62%, #25B0CF 62%)"
    },
    "livery-345": {
        "background": "linear-gradient(to top, #0f3281 30%, #fff 30%, #fff 40%, #f19203 40%, #FF5F15 48%, #fff 48%)",
        "stroke": "#ffffff"
    },
    "livery-346": {
        "background": "linear-gradient(to top, #e31c25 10%, #f5f3e5 10%, #f5f3e5 19%, #fc8638 19%, #fc8638 28%, #e31c25 28%, #e31c25 73%, #f5f3e5 73%, #f5f3e5 82%, #fc8638 82%, #fc8638 91%, #e31c25 91%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#e31c25"
    },
    "livery-347": {
        "background": "linear-gradient(to right, rgb(240, 59, 46) 12%, rgb(216, 181, 82) 12%)",
        "__darkreader_inline_bgcolor": "rgba(0, 0, 0, 0)",
        "__darkreader_inline_bgimage": "linear-gradient(to right, #ad170c 12%, #6d5719 12%)"
    },
    "livery-348": {
        "background": "linear-gradient(to bottom, #1072bd 30%, #e5d7ba 30%, #e5d7ba 60%, #1072bd 60%, #1072bd 70%, #e5d7ba 70%, #e5d7ba 80%, #1072bd 80%, #1072bd 90%, #e5d7ba 90%)",
        "stroke": "#e5d7ba"
    },
    "livery-349": {
        "background_color": "#ff2424",
        "background_image": "linear-gradient(0deg, #3563ffff 19%, transparent 19.05%),linear-gradient(0deg, #f2ce00ff 40%, transparent 40.05%)"
    },
    "livery-350": {
        "background": "linear-gradient(45deg, #AABBC8 10%, #0083BA 10%, #0083BA 25%, transparent 25%), linear-gradient(to top, #0083BA 30%, #AABBC8 30%)",
        "stroke": "#AABBC8"
    },
    "livery-351": {
        "background": "linear-gradient(to right, #e51a7e 20%, #6D8696 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-352": {
        "background": "linear-gradient(to right, #96bd2f 20%, #6D8696 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-353": {
        "background": "linear-gradient(to right, #f2931e 20%, #6D8696 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-354": {
        "background": "linear-gradient(135deg, #B6C740 34%, #2d6294 34%, #2d6294 56%, #25355F 56%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-355": {
        "background": "radial-gradient(circle at top left, #ec98c000 70%, #024f3a 70%), radial-gradient(circle at 10% -6%, #d590 63%, #2a921a 63%), #9bc129",
        "stroke": "#9bc129"
    },
    "livery-356": {
        "background": "linear-gradient(135deg, #F4E939 50%, #275CA8 50%)",
        "stroke": "#F4E939"
    },
    "livery-357": {
        "background": "radial-gradient(circle at -10% -73%, #f3c21d 76%, #e0a030 76% 81%, #bf7e2a 81%)"
    },
    "livery-358": {
        "background": "radial-gradient(circle at 92% 53%, #fff 7%, #0000 7.5%), radial-gradient(circle at 87% 57%, #fff 7%, #0000 7.5%), radial-gradient(circle at 90% 57%, #fff 6%, #bebfc3 6.5%, #bebfc3 7.5%, #0000 8%), radial-gradient(circle at 101% 117%, #006cb9 25%, #0000 25.5%), radial-gradient(circle at 90% 140%, #006cb9 35%, #0000 35.5%), linear-gradient(0deg, #006cb9 12%, #0000 12%), linear-gradient(-40deg, #006cb9 16%, #bebfc3 16.5%, #bebfc3 18.5%, #0000 19%), radial-gradient(circle at 90% 140%, #006cb9 35%, #bebfc3 35.5%, #bebfc3 37.5%, #0000 38%), linear-gradient(0deg, #0000 12%, #bebfc3 12%, #bebfc3 16%, #0000 16%), linear-gradient(0deg, #fff 0%, #fff 100%)"
    },
    "livery-359": {
        "background_color": "#ff2424",
        "background_image": "linear-gradient(0deg, #3563ffff 19%, transparent 19.05%),linear-gradient(180deg, #f2ce00ff 20%, transparent 20.05%)"
    },
    "livery-360": {
        "background_color": "#ff2424",
        "background_image": "linear-gradient(0deg, #3563ffff 19%, transparent 19.05%),linear-gradient(220deg, #f2ce00ff 15%, transparent 15.05%),linear-gradient(45deg, #3563ffff 20%, transparent 20.05%)"
    },
    "livery-361": {
        "background_color": "#ff2424",
        "background_image": "linear-gradient(0deg, #0062c4ff 19%, transparent 19.05%),linear-gradient(45deg, #0062c4ff 20%, transparent 20.05%),linear-gradient(45deg, #ff2424ff 25%, transparent 25.05%),linear-gradient(45deg, #0062c4ff 30%, transparent 30.05%)"
    },
    "livery-362": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(0deg, #0071e4ff 15%, transparent 15.05%),linear-gradient(130deg, #0071e4ff 35%, transparent 35.05%),linear-gradient(0deg, #161616ff 30%, transparent 30.05%)"
    },
    "livery-363": {
        "background": "linear-gradient(300deg, #0000 72%, #ff4283 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-364": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(0deg, #0071e4ff 15%, transparent 15.05%),linear-gradient(130deg, #0071e4ff 35%, transparent 35.05%),linear-gradient(180deg, #161616ff 65%, transparent 65.05%)"
    },
    "livery-365": {
        "background": "linear-gradient(to top, #1b435c 25%, #77b2c4 25%)"
    },
    "livery-366": {
        "background": "linear-gradient(to right, rgb(81, 194, 252) 15%, rgb(247, 184, 68) 15%)",
        "__darkreader_inline_bgcolor": "rgba(0, 0, 0, 0)",
        "__darkreader_inline_bgimage": "linear-gradient(to right, #03679b 15%, #a16b07 15%)"
    },
    "livery-367": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(0deg, #f90000ff 20%, transparent 20.05%), linear-gradient(135deg, #008806ff 20%, transparent 15.05%), radial-gradient(circle at 57% 15%, #ffffffff 55%, transparent 50.05%),linear-gradient(-56deg, #f90000ff 44%, transparent 44.05%)"
    },
    "livery-368": {
        "background": "linear-gradient(135deg, #86BCEA 34%, #F8C327 34%, #F8C327 50%, #2A4177 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#2A4177"
    },
    "livery-369": {
        "background": "linear-gradient(to top, #ae2a2f 34%, #3251AE 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-370": {
        "color": "#fff",
        "fill": "#fff",
        "background": "linear-gradient(#f90000ff 75%,#9f0f06 25%)"
    },
    "livery-371": {
        "background_color": "#000000",
        "background_image": "linear-gradient(-65deg, #000000ff 25%, transparent 25.05%),linear-gradient(-65deg, #e71d22ff 35%, transparent 35.05%),linear-gradient(-65deg, #000000ff 45%, transparent 45.05%),linear-gradient(-65deg, #bc9b16ff 70%, transparent 70.05%)"
    },
    "livery-372": {
        "background": "linear-gradient(135deg, #76B729 34%, #008734 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-373": {
        "background": "linear-gradient(135deg, #E40000 34%, #008834 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-374": {
        "background": "linear-gradient(135deg, #00A6E2 34%, #154377 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-375": {
        "background": "linear-gradient(135deg, #E20512 34%, #004181 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-376": {
        "background": "linear-gradient(135deg, #9972B1 34%, #512584 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-377": {
        "background": "linear-gradient(135deg, #1DA0DB 34%, #0055A4 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-378": {
        "background": "linear-gradient(135deg, #FDDB00 34%, #092C90 34%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#092C90"
    },
    "livery-379": {
        "background": "linear-gradient(300deg, #0000 72%, #f15a29 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-380": {
        "background": "linear-gradient(300deg, #0000 72%, #c50004 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-381": {
        "background": "linear-gradient(300deg, #0000 72%, #009eda 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-382": {
        "background": "linear-gradient(300deg, #0000 72%, #02943f 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-383": {
        "background": "linear-gradient(300deg, #0000 72%, #30444d 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-384": {
        "background": "linear-gradient(300deg, #0000 72%, #f599b1 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-385": {
        "background_color": "#fdae1c",
        "background_image": "linear-gradient(108deg, #bd1e1aff 50%, transparent 50.05%),linear-gradient(108deg, #fdae1cff 55%, transparent 55.05%),linear-gradient(108deg, #bd1e1aff 60%, transparent 60.05%)"
    },
    "livery-386": {
        "background": "linear-gradient(300deg, #0000 72%, #00a7ac 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-387": {
        "background": "linear-gradient(300deg, #0000 72%, #80298f 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-389": {
        "background": "linear-gradient(115deg, #018A3C 50%, #D1D83E 50%)"
    },
    "livery-390": {
        "background": "linear-gradient(135deg, #D287B9 34%, #874490 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-391": {
        "background_color": "#000000",
        "background_image": "linear-gradient(-180deg, #00b3ffff 71%, transparent 71.05%),linear-gradient(0deg, #002aff9f 50%, transparent 50.05%)"
    },
    "livery-392": {
        "background": "linear-gradient(135deg, #e10f22 34%, #fdcd2d 34%)"
    },
    "livery-393": {
        "background": "linear-gradient(135deg, #00829D 34%, #F9B105 34%)"
    },
    "livery-394": {
        "background": "linear-gradient(135deg, #408444 34%, #FAB001 34%)"
    },
    "livery-395": {
        "background": "linear-gradient(135deg, #031196 34%, #fdbf2d 34%)",
        "stroke": "#fdbf2d"
    },
    "livery-396": {
        "background": "linear-gradient(135deg, #EF8E4A 34%, #FEDA45 34%)"
    },
    "livery-398": {
        "background": "radial-gradient(circle at top, #86ba27 50%, #464644 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-399": {
        "background": "linear-gradient(110deg, #70eb29 64%, #ffffff 64%, #ffffff 73%, #208b78 73%)",
        "stroke": "#70eb29"
    },
    "livery-401": {
        "background": "#A3191F",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-402": {
        "background": "linear-gradient(to right, #ED1B23 55%, #ffffff 55%, #ffffff 64%, #15601E 64%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-404": {
        "background": "linear-gradient(285deg, #fff 7%, #c0c0c0 7%, #c0c0c0 34%, #ec5c96 34%, #ec5c96 54%, #fff 54%, #fff 60%, #842181 60%, #842181 74%, #fff 74%)",
        "color": "#000000",
        "fill": "#000000",
        "stroke": "#FFFFFF"
    },
    "livery-405": {
        "background": "linear-gradient(to right, #79b33b 50%, #005E39 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-406": {
        "background": "linear-gradient(to top, #142b6a 25%, #f1e3aa 25%, #f1e3aa 50%, #142b6a 50%, #142b6a 75%, #f1e3aa 75%)",
        "stroke": "#ffffff"
    },
    "livery-409": {
        "background": "linear-gradient(to top, #395ca3 34%, #ffffff 34%)",
        "stroke": "#ffffff"
    },
    "livery-410": {
        "background": "linear-gradient(to top, #395ca3 40%, #d7c0a1 40%, #d7c0a1 60%, #ffffff 60%)"
    },
    "livery-411": {
        "background": "linear-gradient(to top, #4c4f53 15%, #ebb730 15%, #ebb730 20%, #dc241f 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-412": {
        "background": "linear-gradient(to right, #b9c4ca 20%, #F9E300 20%)"
    },
    "livery-413": {
        "background": "linear-gradient(to right, #9c57cb 20%, #F9E300 20%)"
    },
    "livery-414": {
        "background": "linear-gradient(to right, #0ea36f 20%, #F9E300 20%)"
    },
    "livery-415": {
        "background": "linear-gradient(to top, #2B5D64 20%, transparent 20%), radial-gradient(circle at 0% 42%, #29BFCF 5%, #29BFCF 39%, transparent 20%), radial-gradient(circle at 16% 32%, #F0F0C8 5%, #F0F0C8 35%, transparent 20%, #29BFCF 20%)"
    },
    "livery-416": {
        "background": "#09493E",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-420": {
        "background": "linear-gradient(to top, #4ca3fb 20%, #F9E300 20%)"
    },
    "livery-455": {
        "background": "linear-gradient(to right, #fef7b6 75%, #7b5b61 75%)"
    },
    "livery-456": {
        "background": "linear-gradient(300deg, #01465d 28%, #0000 28%), linear-gradient(to top, #0098b0 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #ec2a0c 31%, #0c4340 39%, #0000 39%), linear-gradient(to top, #0098b0 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #f48723 20%), #0098b0",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-457": {
        "background": "linear-gradient(to top, #11b16b 28%, #ffffff 28%, #ffffff 37%, #9e48a0 37%, #9e48a0 46%, #ffffff 46%)",
        "stroke": "#ffffff"
    },
    "livery-460": {
        "background": "linear-gradient(to top, #c43b29 34%, #d6e5ec 34%)"
    },
    "livery-461": {
        "background": "linear-gradient(to top, #bd0000 20%, transparent 20%, transparent 40%, #bd0000 40%), linear-gradient(135deg, #FFFD38 70%, #bd0000 70%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#bd0000"
    },
    "livery-462": {
        "background": "linear-gradient(180deg, transparent 80%, #143b8d 80%), radial-gradient(circle at left, #dfdfe6 70%, #143b8d 70%)",
        "stroke": "#dfdfe6"
    },
    "livery-463": {
        "background": "linear-gradient(300deg, #0000 72%, #05A7FF 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-467": {
        "background": "linear-gradient(60deg, transparent 65%, #fff 65%, #fff 70%, transparent 70%), linear-gradient(110deg, transparent 70%, #337f6a 70%), linear-gradient(60deg, transparent 65%, #36ac71 65%), linear-gradient(to top, #eed878 20%, #cba85f 20%)",
        "stroke": "#eed878"
    },
    "livery-468": {
        "background": "linear-gradient(to top, #45525e 34%, #ff975a 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-469": {
        "background": "#fff957"
    },
    "livery-471": {
        "background": "radial-gradient(circle at right, #00a52f 67%, #fff 67%)"
    },
    "livery-472": {
        "background": "linear-gradient(to right, #c7c7c7 34%, #e6202f 34%, #e6202f 67%, #c7c7c7 67%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#e6202f"
    },
    "livery-474": {
        "background": "linear-gradient(to top, #1137a9 40%, #e9e6ef 40%, #e9e6ef 80%, #1137a9 80%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#1137a9"
    },
    "livery-475": {
        "background": "radial-gradient(circle at 38% 5%, #fbf8f1 60%, #d5323c 60%)",
        "stroke": "#fbf8f1"
    },
    "livery-476": {
        "background": "linear-gradient(60deg, transparent 65%, #fff 65%, #fff 70%, transparent 70%), linear-gradient(110deg, transparent 70%, #1b1b1d 70%), linear-gradient(60deg, transparent 65%, #515863 65%), linear-gradient(to top, #eed878 20%, #cba85f 20%)",
        "stroke": "#eed878"
    },
    "livery-515": {
        "background": "linear-gradient(to top, #002679 20%, #C11D30 20%, #C11D30 30%, #002679 30%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-517": {
        "background": "linear-gradient(45deg, #E30315 40%, #074787 40%, #074787 80%, #7ac1fb 80%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-519": {
        "background": "linear-gradient(to top, #7b1414 50%, #fff 50%)",
        "stroke": "#FFFFFF"
    },
    "livery-521": {
        "background": "linear-gradient(to top, #eeedde 38%, #7c52d2 38%, #7c52d2 63%, #eeedde 63%)",
        "stroke": "#eeedde"
    },
    "livery-522": {
        "background": "linear-gradient(120deg, #64656a 40%, #ffff 40%)",
        "stroke": "#ffffff"
    },
    "livery-524": {
        "background": "linear-gradient(to top, #3f4073 19%, #AB985A 19%, #AB985A 28%, #758CFE 28%, #758CFE 46%, #464FB8 46%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-527": {
        "background": "linear-gradient(to top, #5768A0 19%, #E0EFFA 19%, #E0EFFA 28%, #82E06C 28%, #82E06C 46%, #E0EFFA 46%)"
    },
    "livery-529": {
        "background": "linear-gradient(45deg, #ffe010 40%, #c22e86 40%, #c22e86 80%, #ffe010 80%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#c22e86"
    },
    "livery-530": {
        "background": "linear-gradient(135deg, #c5c4c0 29%, #b46b29 29%, #b46b29 36%, #9d1f1d 36%, #9d1f1d 43%, #275d7b 43%, #275d7b 50%, #062a63 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-532": {
        "background": "linear-gradient(to top, #3149e8 25%, #ffffff 25%)"
    },
    "livery-534": {
        "background": "linear-gradient(300deg, #0000 72%, #d5137e 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-535": {
        "background": "linear-gradient(to top, #fff 20%, #949b9c 20%, #949b9c 40%, #283649 40%, #283649 60%, #fff 60%)",
        "stroke": "#ffffff"
    },
    "livery-538": {
        "background": "linear-gradient(to top, #2B5D64 20%, #FFD800 20%, #FFD800 24%, transparent 24%), radial-gradient(at top left, #29BFCF 22%, #6e3697 22%, #6e3697 24%, #3c75d1 24%, #3c75d1 28%, #67b643 28%, #67b643 32%, #e2c430 32%, #e2c430 36%, #ec9629 36%, #ec9629 40%, #db3a31 40%, #db3a31 44%, #29BFCF 44%), linear-gradient(to top, #FFD800 20%, #FFD800 24%, transparent 0%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-539": {
        "background": "linear-gradient(115deg, #7A77B7 35.5%, #6b538e 36%, #6b538e 40%, #d3d3d3 41%, #fff 45%, #26214E 45.5%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-540": {
        "background": "linear-gradient(130deg, #6193c8 38%, #fed809 38%, #fed809 50%, #001954 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#043478"
    },
    "livery-542": {
        "background": "#505357",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#505357"
    },
    "livery-545": {
        "background": "#ffffff"
    },
    "livery-546": {
        "background": "linear-gradient(to top, #4476ce 34%, #fff 34%)"
    },
    "livery-547": {
        "background": "linear-gradient(30deg, #D61208 45%, #E0752C 45%, #E0752C 56%, #9E000A 56%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-548": {
        "background": "linear-gradient(to top, #ED1D23 25%, #1F2879 25%, #1F2879 50%, #ffffff 50%)",
        "stroke": "#ffffff"
    },
    "livery-549": {
        "background": "linear-gradient(to top, #6a98bc 34%, #b6bdc5 34%)"
    },
    "livery-550": {
        "background": "radial-gradient(at bottom right, #38579a 55%, #fff 55%)",
        "stroke": "#ffffff"
    },
    "livery-552": {
        "background": "linear-gradient(100deg, #4e80f5 34%, #fff 34%, #fff 67%, #f03e34 67%)",
        "stroke": "#ffffff"
    },
    "livery-553": {
        "background": "linear-gradient(180deg, #d5323c 30%, #0000 30%, #fbf8f1 30%, #fbf8f1 60%, #0000 60%, #0000 85%, #d5323c 85%, #d5323c 90%, #fbf8f1 90%), linear-gradient(90deg, #fbf8f1 30%, #0000 30%), radial-gradient(circle at 37% 50%, #fbf8f1 30%, #0000 30%), linear-gradient(180deg, #fbf8f1 55%, #d5323c 55%, #d5323c 60%, #d5323c 60%, #d5323c 80%, #fbf8f1 80%)"
    },
    "livery-554": {
        "background": "radial-gradient(circle at top, #ca84cb 50%, #303636 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-556": {
        "background": "linear-gradient(45deg, #6cc8f4 24%, #ffffff 24%, #ffffff 31%, #3086c6 31%, #3086c6 47%, #ffffff 47%, #ffffff 54%, #3086c6 54%, #3086c6 85%, #ffffff 85%, #ffffff 93%, #3086c6 93%)",
        "stroke": "#ffffff"
    },
    "livery-558": {
        "background": "#6e2447",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-559": {
        "background": "#FFF5A4"
    },
    "livery-560": {
        "background": "linear-gradient(135deg, #fbac48 40%, #062a63 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-561": {
        "background": "linear-gradient(to top, #067C2D 34%, #0DD82E 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-563": {
        "background": "linear-gradient(135deg, #f5dc25 20%, transparent 40%), linear-gradient(to top, #067C2D 33%, #0DD82E 33%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-564": {
        "background": "radial-gradient(circle at -20% 0, #14346B 48%, #c3feff 48%, #c3feff 51%, #11B2D6 51%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-565": {
        "background": "linear-gradient(to right, #009fe4 50%, #004480 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-566": {
        "background": "linear-gradient(to top, #feb913 20%, #283a7f 20%, #283a7f 40%, #ffffff 40%, #ffffff 60%, #283a7f 60%)",
        "stroke": "#ffffff"
    },
    "livery-568": {
        "background": "linear-gradient(280deg, #cccdd0 34%, #8e3b8e 34%, #8e3b8e 67%, #cccdd0 67%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#8e3b8e"
    },
    "livery-569": {
        "background": "linear-gradient(to top, rgb(12, 100, 194) 20%, transparent 20%, transparent 60%, rgb(255, 188, 0) 60%), linear-gradient(135deg, rgb(255, 188, 0) 70%, rgb(12, 100, 194) 70%)"
    },
    "livery-571": {
        "background": "linear-gradient(135deg, #FF911E 40%, #FF561C 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-574": {
        "background": "linear-gradient(to right, #26272C 29%, #5E6060 29%, #5E6060 43%, #FE0000 43%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-575": {
        "background": "#E5007A",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-576": {
        "background": "linear-gradient(to top, #0f6f4d 41%, #efd990 41%, #efd990 47%, #0f6f4d 47%, #0f6f4d 53%, #efd990 53%, #efd990 59%, #0f6f4d 59%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#0f6f4d"
    },
    "livery-577": {
        "background": "#5792EC",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-578": {
        "background": "radial-gradient(circle at left 45%, #e22 35%, #510 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-579": {
        "background": "radial-gradient(circle at left 45%, #3bc 35%, #077 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-580": {
        "background": "linear-gradient(300deg, #0000 72%, #9183be 20%), linear-gradient(300deg, #402886 28%, #0000 28%), linear-gradient(to top, #9183be 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #f8a51b 31%, #f8a51b 39%, #0000 39%), #9183be",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-581": {
        "background": "linear-gradient(125deg, #0ca8d1 34%, #46d8e8 34%, #46d8e8 67%, #2898ae 67%)"
    },
    "livery-582": {
        "background": "linear-gradient(300deg, #0000 72%, #f39a1f 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-583": {
        "background": "linear-gradient(to right, #ffcb43 50%, #b1a98d 50%, #b1a98d 67%, #ffcb43 67%, #ffcb43 84%, #b1a98d 84%)",
        "stroke": "#ffbf00"
    },
    "livery-584": {
        "background": "linear-gradient(to right, #02bdb9 13%, #ffffff 13%, #ffffff 63%, #02bdb9 63%, #02bdb9 75%, #ffffff 75%, #ffffff 88%, #02bdb9 88%)",
        "stroke": "#ffffff"
    },
    "livery-585": {
        "background": "#FFD400"
    },
    "livery-586": {
        "background": "#fd6000",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-587": {
        "background": "radial-gradient(ellipse at 20% 134%, #0055bb 30%, transparent 30%), radial-gradient(ellipse at 51% 16%, #11bbff 60%, transparent 0%), linear-gradient(80deg, #11bbff 0%, #11bbff 31%, transparent 10%), radial-gradient(ellipse at 50% 17%, #11bbff 60%, #0000 10%), radial-gradient(ellipse at 50% 16%, #0055bb 60%, #0055bb 0%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-588": {
        "background": "linear-gradient(300deg, #0000 72%, #b5831e 20%), linear-gradient(300deg, #8c4411 28%, #0000 28%), linear-gradient(to top, #f1b52d 15%, #0000 15%), linear-gradient(120deg, #f1b52d 61%, #0000 61%, #0000 69%, #f1b52d 69%), #fec934",
        "stroke": "#f1b52d"
    },
    "livery-590": {
        "background": "linear-gradient(to top, #0cbf86 50%, #b9eba1 50%)"
    },
    "livery-596": {
        "background": "linear-gradient(300deg, #0000 72%, #f73f2d 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-597": {
        "background": "#8A0202",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-599": {
        "background": "radial-gradient(ellipse at -80% 180%, transparent 75%, #037 75%), radial-gradient(ellipse at -60% 260%, #18d 75%, #bdf 75%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#003377"
    },
    "livery-600": {
        "background": "linear-gradient(to right, #07c4ff 10%, #ffffff 10%, #ffffff 50%, #009879 50%, #009879 60%, #07c4ff 60%, #07c4ff 70%, #ffffff 70%, #ffffff 90%, #faae00 90%)",
        "stroke": "#ffffff"
    },
    "livery-633": {
        "background": "linear-gradient(to left, #4B2580 50%, transparent 50%), radial-gradient(circle at center, #4B2580 58%, #b7a8e8 58%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-636": {
        "background": "radial-gradient(circle at 54% 46%, #0a8 49%, #fff0 49%), radial-gradient(circle at 50% 50%, #7ed 56%, #fff0 56%), linear-gradient(270deg, #0a8 50%, #155 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-637": {
        "background": "radial-gradient(circle at 54% 46%, #712 49%, #fff0 49%), radial-gradient(circle at 50% 50%, #913 56%, #fff0 56%), linear-gradient(270deg, #712 50%, #301 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-638": {
        "background": "radial-gradient(circle at 54% 46%, #A38142 49%, #fff0 49%), radial-gradient(circle at 50% 50%, #753 56%, #fff0 56%), linear-gradient(90deg, #f2b946 50%, #A38142 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-639": {
        "background": "radial-gradient(circle at 54% 46%, #148 49%, #fff0 49%), radial-gradient(circle at 50% 50%, #0be 56%, #fff0 56%), linear-gradient(270deg, #148 50%, #08c 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-640": {
        "background": "radial-gradient(circle at 54% 46%, #fd6 49%, #fff0 49%), radial-gradient(circle at 50% 50%, #ffa 56%, #fff0 56%), linear-gradient(270deg, #fd6 50%, #b95 50%)"
    },
    "livery-641": {
        "background": "#68c9f6"
    },
    "livery-643": {
        "background": "linear-gradient(0deg, #fff 55%, transparent 55%), linear-gradient(120deg, #fff 52%, #b7bbcb 52%, #b7bbcb 56%, #fff 56%, #fff 60%, #b7bbcb 60%, #b7bbcb 64%, #fff 64%, #fff 68%, #b7bbcb 68%, #b7bbcb 72%, #fff 72%, #fff 76%, #b7bbcb 76%, #b7bbcb 80%, #fff 80%, #fff 84%)"
    },
    "livery-644": {
        "background": "radial-gradient(ellipse at 23% 140%, #C71A26 31%, transparent 31%), radial-gradient(circle at 51% 42%, #F3F1E5 49%, transparent 0%), linear-gradient(109deg, #F3F1E5 1%, #F3F1E5 46%, transparent 10%), linear-gradient(3deg, #C71A26 20%, #0000 20%), radial-gradient(circle at 45% 24%, #2B3F8A 60%, transparent 10%), linear-gradient(to top, #C71A26 20%, #C71A26 20%)",
        "stroke": "#F3F1E5"
    },
    "livery-645": {
        "background": "#34fdd3"
    },
    "livery-646": {
        "background": "linear-gradient(to top, #13b3ff 34%, #0f3192 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-647": {
        "background": "radial-gradient(at top left, #fff 30%, #fd0 20%)"
    },
    "livery-680": {
        "background": "linear-gradient(135deg, #b2fb16 40%, #062a63 40%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#062a63"
    },
    "livery-681": {
        "background": "linear-gradient(to left, #39d 50%, transparent 50%), radial-gradient(circle at center, #39d 58%, #07b 58%)"
    },
    "livery-682": {
        "background": "linear-gradient(to left, #cc33aa 50%, transparent 50%), radial-gradient(circle at center, #cc33aa 58%, #a01080 58%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-683": {
        "background": "radial-gradient(circle at top, #d7dcda 50%, #464644 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#464644"
    },
    "livery-689": {
        "background": "linear-gradient(300deg, #0000 72%, #21605c 20%), linear-gradient(to top, #5768A0 20%, #75b91a 20%, #75b91a 27%, #A9B8E3 27%, #A9B8E3 47%, #E0EFFA 47%)"
    },
    "livery-691": {
        "background": "linear-gradient(300deg, #0000 72%, #50caf2 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-692": {
        "background": "linear-gradient(300deg, #068 28%, #0000 28%), linear-gradient(to top, #fd0 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #f90 31%, #f90 39%, #0000 39%), #fd0",
        "stroke": "#ffdd00"
    },
    "livery-694": {
        "background": "linear-gradient(to right, #32ecbc 39%, #fff 39%, #fff 47%, #32ecbc 47%, #32ecbc 77%, #fff 77%, #fff 85%, #32ecbc 85%)"
    },
    "livery-695": {
        "background": "linear-gradient(to right, #C8F25E 67%, #15601E 67%)",
        "stroke": "#C8F25E"
    },
    "livery-696": {
        "background": "#ff2222",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-697": {
        "background": "#ff2222",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-698": {
        "background": "linear-gradient(340deg, #7a0c0a 34%, #e9d4a6 34%)"
    },
    "livery-699": {
        "background": "linear-gradient(180deg, #0000 50%, #3be 50%), repeating-conic-gradient(from 18deg, #09d 12deg 24deg, #3be 24deg 36deg)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-700": {
        "background": "radial-gradient(ellipse at 23% 140%, #8b221f 31%, transparent 31%), radial-gradient(circle at 51% 42%, #e00001 49%, transparent 0%), linear-gradient(109deg, #e00001 1%, #e00001 46%, transparent 10%), linear-gradient(3deg, #8b221f 20%, #8b221f 20%), radial-gradient(circle at 45% 24%, #000 60%, transparent 10%), linear-gradient(to top, #8b221f 20%, #8b221f 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-706": {
        "background": "linear-gradient(300deg, #cc1122 28%, #0000 28%), linear-gradient(to top, #ffee66 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #ff9910 31%, #ff9910 39%, #0000 39%), linear-gradient(to top, #ffee66 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #ff9910 20%), #fe6",
        "stroke": "#ffee66"
    },
    "livery-707": {
        "background": "linear-gradient(300deg, #0000 72%, #18a654 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-710": {
        "background": "radial-gradient(circle at left 45%, #2cf 35%, #06c 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-713": {
        "background": "linear-gradient(300deg, #ee1c25 38%, #72001a 38%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-715": {
        "background": "linear-gradient(300deg, #091c63 28%, #0000 28%), linear-gradient(to top, #337ebf 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #ceab5f 31%, #ceab5f 39%, #0000 39%), #337ebf",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-716": {
        "background": "linear-gradient(300deg, #0000 72%, #79da34 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-717": {
        "background": "linear-gradient(135deg, #f5851f 34%, #662a8f 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-720": {
        "background": "linear-gradient(to right, #0177cb 19%, #fff 19%, #fff 46%, #0177cb 46%, #0177cb 64%, #fff 64%, #fff 91%, #0177cb 91%)"
    },
    "livery-721": {
        "background": "linear-gradient(300deg, #0000 72%, #d5137e 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-722": {
        "background": "radial-gradient(circle at -50% 25%, #1F2D6B 48%, #6e3697 48%, #6e3697 52%, #3c75d1 52%, #3c75d1 56%, #67b643 56%, #67b643 60%, #e2c430 60%, #e2c430 64%, #ec9629 64%, #ec9629 68%, #db3a31 68%, #db3a31 72%, #2ABBEA 66%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-723": {
        "background": "radial-gradient(ellipse at 35% -45%, #ed4d80 45%, transparent 45%), linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-724": {
        "background": "radial-gradient(ellipse at 35% -45%, #3ac3e4 45%, transparent 45%), linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-725": {
        "background": "radial-gradient(ellipse at 35% -45%, #37e32f 45%, transparent 45%), linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-726": {
        "background": "radial-gradient(ellipse at 35% -45%, #03d5e4 45%, transparent 45%), linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-727": {
        "background": "radial-gradient(ellipse at top left, #1c6325 25%, #6ad52c 15% 27%, #0000 15%), linear-gradient(to top, #1c6325 15%, #1c60 15%), linear-gradient(352deg, #1c6325 23.4%, #1c60 15%), linear-gradient(346deg, #1c6325 27.22%, #1c60 15%), linear-gradient(to top, #6ad52c 18%, #1c60 15%), linear-gradient(to right, #eee4d7 34%, #0000 20%), radial-gradient(circle at 33% 0%, #eee4d7 58%, #6ad52c 58% 60%, #1c6325 22%)"
    },
    "livery-728": {
        "background": "linear-gradient(to top, #004993 50%, #43AC49 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-729": {
        "background": "#7BC816"
    },
    "livery-730": {
        "background": "linear-gradient(248deg, #0c4a69 30%, #14b3c1 30%, #14b3c1 34%, #0c4a69 34%, #0c4a69 38%, #14b3c1 38%, #14b3c1 41%, #0c4a69 41%, #0c4a69 45%, #14b3c1 45%, #14b3c1 49%, #0c4a69 49%, #0c4a69 52%, #14b3c1 52%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-731": {
        "background": "radial-gradient(circle at 50% 196%, #2e1f75 58%, #0000 0%), radial-gradient(circle at 50% 67%, #fff -16%, #2e1f75 56%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#2e1f75"
    },
    "livery-732": {
        "background": "linear-gradient(to right, #0F6DB4 20%, #ffffff 20%, #ffffff 40%, #e04a78 40%, #e04a78 60%, #F79F48 60%, #F79F48 80%, #EA2639 80%)",
        "stroke": "#ffffff"
    },
    "livery-734": {
        "background": "linear-gradient(to top, #D41B2B 20%, #F5E7B8 20%, #F5E7B8 50%, #D41B2B 50%, #D41B2B 70%, #F5E7B8 70%, #F5E7B8 80%, #D41B2B 80%)",
        "stroke": "#F5E7B8"
    },
    "livery-735": {
        "background": "linear-gradient(120deg, #d2e03a 67%, #25552c 67%)"
    },
    "livery-736": {
        "background": "linear-gradient(300deg, #f80 28%, #0000 28%), linear-gradient(to top, #08d 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #fd0 31%, #fd0 39%, #0000 39%), linear-gradient(to top, #08d 60%, #08d 60%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#0085d0"
    },
    "livery-737": {
        "background": "#50388c",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-739": {
        "background": "radial-gradient(circle at -50% 25%, #0D2247 48%, #6e3697 48%, #6e3697 52%, #3c75d1 52%, #3c75d1 56%, #67b643 56%, #67b643 60%, #e2c430 60%, #e2c430 64%, #ec9629 64%, #ec9629 68%, #db3a31 68%, #db3a31 72%, #0EA0C1 66%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-740": {
        "background": "linear-gradient(300deg, #0000 72%, #009eda 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-742": {
        "background": "#429194",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-746": {
        "background": "linear-gradient(60deg, transparent 65%, #fff 65%, #fff 70%, transparent 70%), linear-gradient(110deg, transparent 70%, #37c500 70%), linear-gradient(60deg, transparent 65%, #8ff400 65%), linear-gradient(to top, #eed878 20%, #cba85f 20%)",
        "stroke": "#eed878"
    },
    "livery-748": {
        "background": "radial-gradient(ellipse at 35% -45%, #007ef1 45%, transparent 45%), linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-749": {
        "background": "radial-gradient(ellipse at 35% -45%, #46aceb 45%, transparent 45%), linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-751": {
        "background": "linear-gradient(90deg, #da7f2f 10%, #1f3f7b 10%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-752": {
        "background": "linear-gradient(to top, #913395 25%, #e6038c 25%, #e6038c 50%, #913395 50%, #913395 75%, #e6038c 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-753": {
        "background": "linear-gradient(60deg, #deaf0b 59%, #136e42 59%, #136e42 67%, #deaf0b 67%, #deaf0b 75%, #136e42 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-754": {
        "background": "linear-gradient(70deg, transparent 40%, #1175fb 40%), linear-gradient(180deg, #fdec5a 80%, #1175fb 80%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-756": {
        "background": "linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #72def4 60%, #72def4 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-757": {
        "background": "linear-gradient(110deg, #FDEC80 34%, #ECC178 34%, #ECC178 50%, #AD9044 50%, #AD9044 67%, #A30A2F 67%)",
        "color": "#A30A2F",
        "fill": "#A30A2F",
        "stroke": "#FDEC80"
    },
    "livery-758": {
        "background": "linear-gradient(60deg, #ed1b23 35%, #d3d3d3 35.1% 39%, #fff 39.1% 43%, #ed1b23 43.1% 47%, #000 47.1%)",
        "color": "#ffffff",
        "fill": "#ffffff",
        "stroke": "#000000"
    },
    "livery-759": {
        "background": "linear-gradient(to right, #35baff 80%, #2853ef 80%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-760": {
        "background": "linear-gradient(300deg, #0000 72%, #ecd66e 20%), linear-gradient(300deg, #07256e 28%, #0000 28%), linear-gradient(to top, #ecd66e 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #0081de 31%, #0081de 39%, #0000 39%), #ecd66e",
        "stroke": "#ecd66e"
    },
    "livery-761": {
        "background": "linear-gradient(300deg, #0000 72%, #e41e26 20%), linear-gradient(300deg, #6f0f16 28%, #0000 28%), linear-gradient(to top, #e41e26 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a51e22 31%, #a51e22 39%, #0000 39%), #e41e26",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-762": {
        "background": "linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #6fd6eb 0, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)"
    },
    "livery-763": {
        "background": "linear-gradient(to top, #a41d21 20%, #ed1c24 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-764": {
        "background": "linear-gradient(110deg, #ffe511 55%, #fbef39 55%, #fbef39 64%, #fff 64%, #fff 73%, #8c0005 73%)",
        "stroke": "#FFE511"
    },
    "livery-766": {
        "background": "linear-gradient(110deg, #E51F29 17%, #ED7807 17%, #ED7807 34%, #FCCC11 34%, #FCCC11 50%, #82B648 50%, #82B648 67%, #39A8D7 67%, #39A8D7 84%, #524E9F 84%)"
    },
    "livery-767": {
        "background": "linear-gradient(to right, #fef484 40%, #93c11f 40%, #93c11f 60%, #08983a 60%, #08983a 80%, #005926 80%)"
    },
    "livery-768": {
        "background": "linear-gradient(300deg, #0000 72%, #d5137e 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-769": {
        "background": "linear-gradient(300deg, #0000 72%, #2e932c 20%), linear-gradient(300deg, #01341a 28%, #0000 28%), linear-gradient(to top, #6ec245 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #2e932c 31%, #2e932c 39%, #0000 39%), #6ec245",
        "stroke": "#FFFFFF"
    },
    "livery-770": {
        "background": "linear-gradient(to top, #f4e8cf 43%, #45903a 43%, #45903a 58%, #f4e8cf 58%)"
    },
    "livery-771": {
        "background": "linear-gradient(140deg, #25234B 0%, #25234B 40%, #0000 40%), linear-gradient(140deg, #fbb900 40%, #fbb900 41%, #0000 41%), linear-gradient(148deg, #DD571F 41%, #DD571F 46.5%, #fbb900 46.5%, #fbb900 47.5%, #0000 47.5%), linear-gradient(240deg, #0000 95%, #fbb900 95%, #fbb900 97%), linear-gradient(180deg, #0000 69.5%, #FFFFFF 60%, #FFFFFF 71%, #0000 50%), linear-gradient(140deg, #fbb900 0%, #fbb900 50%)",
        "stroke": "#fbb900"
    },
    "livery-774": {
        "background": "linear-gradient(60deg, transparent 65%, #fff 65%, #fff 70%, transparent 70%), linear-gradient(110deg, transparent 70%, #8c3e61 70%), linear-gradient(60deg, transparent 65%, #d25c9b 65%), linear-gradient(to top, #eed878 20%, #cba85f 20%)",
        "stroke": "#eed878"
    },
    "livery-775": {
        "background": "linear-gradient(60deg, transparent 65%, #fff 65%, #fff 70%, transparent 70%), linear-gradient(110deg, transparent 70%, #94000a 70%), linear-gradient(60deg, transparent 65%, #bc0000 65%), linear-gradient(to top, #eed878 20%, #cba85f 20%)",
        "stroke": "#eed878"
    },
    "livery-776": {
        "background": "radial-gradient(circle at -10% -73%, #fff0 76%, #025 76%), radial-gradient(circle at -45% -83%, #dee 76%, #18d 76%)",
        "stroke": "#ddeeee"
    },
    "livery-777": {
        "background": "linear-gradient(to top, #748625 43%, #ddd74e 43%, #ddd74e 58%, #748625 58%)",
        "stroke": "#ddd74e"
    },
    "livery-778": {
        "background": "linear-gradient(to top, #ef191e 23%, #c3c6cf 23%, #c3c6cf 34%, #fdfb2d 34%, #fdfb2d 89%, #ef191e 89%)"
    },
    "livery-779": {
        "background": "linear-gradient(to top, #ffffcc 13%, #132B28 13%, #132B28 38%, #ffffcc 38%)",
        "stroke": "#ffffcc"
    },
    "livery-781": {
        "background": "linear-gradient(120deg, #87fb48 67%, #127134 67%)"
    },
    "livery-782": {
        "background": "linear-gradient(75deg, #e10d17 34%, #0357a3 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-783": {
        "background": "linear-gradient(75deg, #fea453 34%, #0357a3 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-784": {
        "background": "linear-gradient(to top, #3b8bc0 22%, #ebebed 22%, #ebebed 29%, #1a1f31 29%, #1a1f31 50%, #ebebed 50%, #ebebed 58%, #3b8bc0 58%, #3b8bc0 72%, #ebebed 72%, #ebebed 79%, #1a1f31 79%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#3b8bc0"
    },
    "livery-785": {
        "background": "linear-gradient(to top, #3b8bc0 34%, #1a1f31 34%, #1a1f31 45%, #ebebed 45%, #ebebed 56%, #3b8bc0 56%, #3b8bc0 89%, #1a1f31 89%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#3b8bc0"
    },
    "livery-787": {
        "background": "linear-gradient(to right, #b03841 5%, transparent 5%, transparent 85%, #b03841 85%), radial-gradient(circle at 90% 80%, #b03841 65%, #fff 65%, #fff 86%, #b03841 86%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-788": {
        "background": "radial-gradient(at 4% -3%, #0000 60%, #154 60%), radial-gradient(at 31% -14%, #9c2 55%, #9c20 0%), linear-gradient(344deg, #fe9 39%, #9c20 0%), linear-gradient(to top, #fe9 25.5%, #9c20 0%), #9c2",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#115544"
    },
    "livery-789": {
        "background": "linear-gradient(to top, #3f4073 19%, #AB985A 19%, #AB985A 28%, #758CFE 28%, #758CFE 46%, #464FB8 46%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-790": {
        "background": "linear-gradient(to top, #5768A0 19%, #E0EFFA 19%, #E0EFFA 28%, #82E06C 28%, #82E06C 46%, #E0EFFA 46%)"
    },
    "livery-794": {
        "background": "linear-gradient(110deg, #BDBDBE 55%, #fce700 55%, #fce700 64%, #ffffff 64%, #ffffff 73%, #ED1C24 73%)",
        "stroke": "#BDBDBE"
    },
    "livery-796": {
        "background": "linear-gradient(300deg, #173 28%, #0000 28%), linear-gradient(to top, #8f5 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #fd0 31%, #fd0 39%, #0000 39%), linear-gradient(to top, #8f5 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #fd0 20%), #8f5",
        "stroke": "#88ff55"
    },
    "livery-797": {
        "background": "linear-gradient(300deg, #173 28%, #0000 28%), linear-gradient(to top, #8f5 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #173 31%, #173 39%, #0000 39%), linear-gradient(to top, #8f5 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #173 20%), #8f5",
        "stroke": "#87fb48"
    },
    "livery-798": {
        "background": "linear-gradient(300deg, #173 28%, #0000 28%), linear-gradient(to top, #8f5 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #235 31%, #235 39%, #0000 39%), linear-gradient(to top, #8f5 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #235 20%), #87fb48",
        "stroke": "#88ff55"
    },
    "livery-799": {
        "background": "linear-gradient(110deg, #b690f2 55%, #f8c5fd 55%, #f8c5fd 64%, #fff 64%, #fff 73%, #4c3daf 73%)",
        "stroke": "#b690f2"
    },
    "livery-800": {
        "background": "linear-gradient(60deg, transparent 65%, #fff 65%, #fff 70%, transparent 70%), linear-gradient(110deg, transparent 70%, #f39d12 70%), linear-gradient(60deg, transparent 65%, #f4d989 65%), linear-gradient(to top, #eed878 20%, #afa068 20%)",
        "stroke": "#eed878"
    },
    "livery-801": {
        "background": "linear-gradient(130deg, #FEDC00 35%, transparent 35.5%), linear-gradient(to top, #004C98 4%, transparent 4.5%), linear-gradient(250deg, transparent 0%, #004C98 0% 54%, transparent 54.5%), linear-gradient(147deg, transparent 52.5%, #004c98 53% 61%, transparent 61.5%), linear-gradient(139deg, transparent 45.5%, #2278cd 46% 52%, transparent 52.5%), linear-gradient(138deg, transparent 43.5%, #004c98 44% 47%, transparent 47.5%), linear-gradient(130deg, transparent 36.5%, #64b5f6 37% 43%, transparent 43.5%), #004C98",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#004C98"
    },
    "livery-802": {
        "background": "linear-gradient(300deg, #0000 72%, #d5137e 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-803": {
        "background": "linear-gradient(300deg, #3b3662 28%, #0000 28%), linear-gradient(to top, #ff7700 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #e79121 31%, #e79121 39%, #0000 39%), #ff7700",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#ff7700"
    },
    "livery-805": {
        "background": "linear-gradient(300deg, #005093 28%, #0000 28%), linear-gradient(to top, #0097d9 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #5dcaff 31%, #5dcaff 39%, #0000 39%), #0097d9",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#0097d9"
    },
    "livery-809": {
        "background": "#f2eabf"
    },
    "livery-810": {
        "background": "linear-gradient(300deg, #8b001d 28%, #0000 28%), linear-gradient(to top, #ed1d23 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #f7941e 31%, #f7941e 39%, #0000 39%), #ed1d23",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-812": {
        "background": "linear-gradient(300deg, #0000 72%, #FF0000 20%), linear-gradient(300deg, #800E05 28%, #0000 28%), linear-gradient(to top, #FF6D05 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #E4B93E 31%, #E4B93E 39%, #0000 39%), #FF6D05",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-814": {
        "background": "linear-gradient(300deg, #1c222c 28%, #0000 28%), linear-gradient(to top, #2191c4 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #eae9a9 20%), #2191c4",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-815": {
        "background": "linear-gradient(to right, #a5bac7 34%, #004f9f 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-816": {
        "background": "linear-gradient(to top, #ad0f29 7%, #ad0f29 7%, #ad0f29 10%, #71552a 10%, #71552a 13%, #ad0f29 13%, #ad0f29 16%, #71552a 16%, #71552a 19%, #71552a 19%, #71552a 22%, #71552a 22%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-817": {
        "background": "linear-gradient(to top, #00a1d8 25%, #fffaed 25%, #fffaed 50%, #00a1d8 50%, #00a1d8 67%, #fffaed 67%, #fffaed 92%, #00a1d8 92%)",
        "stroke": "#fffaed"
    },
    "livery-818": {
        "background": "linear-gradient(to top, #ad0f29 7%, #71552a 7%, #71552a 10%, #ad0f29 10%, #ad0f29 13%, #71552a 13%, #71552a 16%, #ad0f29 16%, #ad0f29 19%, #71552a 19%, #71552a 22%, #ad0f29 22%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-819": {
        "background": "conic-gradient(from 0deg at 0% 55%, #77b921 0deg 19deg, #0000 18deg 360deg), conic-gradient(from 36deg at 0% 85%, #77b921 0deg 14deg, #0000 14deg 360deg), linear-gradient(359deg, #0000 47%, #c0d731 48%), linear-gradient(330deg, #139559 19%, #77b921 20%, #77b921 43%, #0000 44%), linear-gradient(357deg, #77b921 21%, #0000 20%), #c0d731",
        "stroke": "#c0d731"
    },
    "livery-820": {
        "background": "linear-gradient(to right, #074787 53%, #7ac1fb 53%, #7ac1fb 59%, #E30315 59%, #E30315 77%, #074787 77%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-821": {
        "background": "linear-gradient(300deg, #0000 72%, #ac7a3b 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-823": {
        "background": "linear-gradient(to top, #004a7f 25%, #96bce9 25%)"
    },
    "livery-824": {
        "background": "linear-gradient(to top, #1b435c 25%, #77b2c4 25%)"
    },
    "livery-825": {
        "background": "radial-gradient(circle at left 45%, #3bc 35%, #077 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-826": {
        "background": "radial-gradient(circle at left 45%, #af1 35%, #094 45%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#009944"
    },
    "livery-827": {
        "background": "#2F88C6",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-831": {
        "background": "radial-gradient(ellipse at 20% 134%, #c0c0c0 30%, transparent 30%), radial-gradient(ellipse at 51% 16%, #020202 60%, transparent 0%), linear-gradient(80deg, #020202 0%, #020202 31%, transparent 10%), radial-gradient(circle at 59% 20%, #cff127 0%, #cff127 50%, transparent 20%), radial-gradient(ellipse at 50% 16%, #020202 60%, transparent 10%), radial-gradient(ellipse at 50% 16%, #c0c0c0 60%, #c0c0c0 0%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#020202"
    },
    "livery-835": {
        "background": "linear-gradient(300deg, #173 28%, #0000 28%), linear-gradient(to top, #8f5 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #666 31%, #666 39%, #0000 39%), linear-gradient(to top, #8f5 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #666 20%), #87fb48",
        "stroke": "#88ff55"
    },
    "livery-836": {
        "background": "linear-gradient(to right, #80ff47 50%, #43e5c0 50%)"
    },
    "livery-837": {
        "background": "linear-gradient(to right, #ff6f2c 50%, #d55574 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-838": {
        "background": "#132357",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-839": {
        "background": "radial-gradient(ellipse at 20% 134%, #c0c0c0 30%, transparent 30%), radial-gradient(ellipse at 51% 16%, #020202 60%, transparent 0%), linear-gradient(80deg, #020202 0%, #020202 31%, transparent 10%), radial-gradient(circle at 59% 20%, #c30513 0%, #c30513 50%, transparent 20%), radial-gradient(ellipse at 50% 16%, #020202 60%, transparent 10%), radial-gradient(ellipse at 50% 16%, #c0c0c0 60%, #c0c0c0 0%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#020202"
    },
    "livery-840": {
        "background": "#F7A900"
    },
    "livery-841": {
        "background": "#EEC72D"
    },
    "livery-842": {
        "background": "#EE7222",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-843": {
        "background": "#EAB90C"
    },
    "livery-844": {
        "background": "linear-gradient(to right, #ffa533 60%, #f4773a 60%, #f4773a 80%, #79bf48 80%)"
    },
    "livery-845": {
        "background": "#A82C71",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-846": {
        "background": "#0563AE",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-847": {
        "background": "#373536",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-848": {
        "background": "linear-gradient(110deg, #75d4f8 60%, #044b7d 60%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-849": {
        "color": "#fff",
        "fill": "#fff",
        "background": "radial-gradient(circle at -10% -73%, #339cfd 76%, #7ebefb 76% 81%, #0f358d 81%)"
    },
    "livery-850": {
        "background": "#004A98",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-851": {
        "background": "#005F75",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-852": {
        "background": "#724abd",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-853": {
        "background": "linear-gradient(to right, #dedfe4 20%, #042c80 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-854": {
        "background": "linear-gradient(to top, #d5323c 25%, #fbf8f1 25%, #fbf8f1 50%, #d5323c 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#d5323c"
    },
    "livery-855": {
        "background": "radial-gradient(circle at 66% 140%, #1d215e 55%, transparent 55%), radial-gradient(circle at 85% 130%, #0278D8 65%, transparent 65%), radial-gradient(circle at 85% 100%, #0244BC 70%, #30a7fe 70%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-856": {
        "background": "linear-gradient(to top, #1c6325 15%, #1c60 15%), linear-gradient(352deg, #1c6325 23.4%, #1c60 15%), linear-gradient(346deg, #1c6325 27.22%, #1c60 15%), linear-gradient(to top, #6ad52c 18%, #1c60 15%), linear-gradient(to right, #eee4d7 34%, #0000 20%), radial-gradient(circle at 33% 0%, #eee4d7 58%, #6ad52c 58% 60%, #1c6325 22%)"
    },
    "livery-857": {
        "background": "linear-gradient(to top, #cc181a 34%, #da271e 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-858": {
        "background": "linear-gradient(to top, #f2b624 34%, #fae971 34%)"
    },
    "livery-859": {
        "background": "#cb232b",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-865": {
        "background": "#48055D",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-867": {
        "background": "radial-gradient(circle at 50% 200%, #E5B313 65%, #E5B313 65%, #60CAE8 0%, #60CAE8 70%, #019DE6 50%, #019DE6 56%, #019DE6 56%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-871": {
        "background": "#b32531",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-872": {
        "background": "linear-gradient(to top, #ffa645 34%, #ffffff 34%)"
    },
    "livery-873": {
        "background": "linear-gradient(135deg, #f3a625 34%, #404346 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-874": {
        "background": "linear-gradient(to top, #335084 15%, #f06895 15%, #f06895 29%, #a7eafd 29%, #a7eafd 86%, #335084 86%)"
    },
    "livery-875": {
        "background": "#0947f3",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-876": {
        "background": "linear-gradient(to right, #f9f3c5 75%, #d01c2e 75%)"
    },
    "livery-877": {
        "background": "linear-gradient(to top, #fc5f13 34%, #f99c41 34%)"
    },
    "livery-878": {
        "background": "linear-gradient(to top, #452456 19%, transparent 19%), radial-gradient(circle at top left, transparent 78%, #ffffff 78%, #ffffff 80%, #452456 80%), linear-gradient(to top, #452456 19%, #ffffff 19%, #ffffff 22%, #f2dfc7 22%, #f2dfc7 40%, transparent 40%), radial-gradient(circle at top left, #ffffff 66%, #f2dfc7 66%, #f2dfc7 78%, #ffffff 78%, #ffffff 80%, #452456 80%)"
    },
    "livery-879": {
        "background": "linear-gradient(to top, #2682d9 34%, #56b4f5 34%)"
    },
    "livery-880": {
        "background": "linear-gradient(to top, #6d3729 29%, #eee4c1 29%, #eee4c1 86%, #6d3729 86%)",
        "stroke": "#eee4c1"
    },
    "livery-882": {
        "background": "linear-gradient(to top, #226fbd 33.3%, #fff 33.3% 66.6%, #62cfbc 66.6%)"
    },
    "livery-883": {
        "background": "#d4b480"
    },
    "livery-884": {
        "background": "linear-gradient(to right, #fff 50%, #fed739 50%, #fed739 75%, #283a79 75%)",
        "stroke": "#ffffff"
    },
    "livery-885": {
        "background": "linear-gradient(to top, #05a1e8 34%, #fff 34%)"
    },
    "livery-887": {
        "background": "linear-gradient(to top, #dc2321 17%, #fff 17%)"
    },
    "livery-889": {
        "background": "linear-gradient(300deg, #421820 28%, #0000 28%), linear-gradient(to top, #be151e 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9599c 31%, #a9599c 39%, #0000 39%), linear-gradient(to top, #be151e 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #eae9a9 20%), #be151e",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-891": {
        "background": "linear-gradient(to top, #031b3f 25%, #bd1725 25%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-892": {
        "background": "radial-gradient(circle at left 45%, #8c2 35%, #482 45%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#448822"
    },
    "livery-894": {
        "background": "linear-gradient(to top, #ff7521 19%, #feeedb 19%, #feeedb 64%, #ff7521 64%, #ff7521 73%, #feeedb 73%, #feeedb 82%, #ff7521 82%, #ff7521 91%, #feeedb 91%)"
    },
    "livery-895": {
        "background": "linear-gradient(to top, #fc3829 20%, #fdffd7 20%)"
    },
    "livery-896": {
        "background": "linear-gradient(130deg, #FEDC00 35%, transparent 35.5%), linear-gradient(to top, #004C98 4%, transparent 4.5%), linear-gradient(250deg, transparent 0%, #004C98 0% 54%, transparent 54.5%), linear-gradient(147deg, transparent 52.5%, #004c98 53% 61%, transparent 61.5%), linear-gradient(139deg, transparent 45.5%, #2278cd 46% 52%, transparent 52.5%), linear-gradient(138deg, transparent 43.5%, #004c98 44% 47%, transparent 47.5%), linear-gradient(130deg, transparent 36.5%, #64b5f6 37% 43%, transparent 43.5%), #004C98",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#004C98"
    },
    "livery-897": {
        "background": "linear-gradient(135deg, #FFDD00 34%, #FAB001 34%)"
    },
    "livery-898": {
        "background": "linear-gradient(135deg, #fce331 34%, #fcb939 34%)"
    },
    "livery-899": {
        "background": "linear-gradient(to top, #137340 25%, #ffffff 25%)"
    },
    "livery-900": {
        "background": "linear-gradient(to right, #fff377 67%, #0285ca 67%)"
    },
    "livery-901": {
        "background": "#1EACE4",
        "color": "#ffffff",
        "fill": "#ffffff"
    },
    "livery-902": {
        "background": "conic-gradient(from 180deg at 49% 75%, #0000 0deg 270deg, #899aae 270deg), linear-gradient(360deg, #899aae00 25%, #65c36300 25% 33%, #576d82 33%), radial-gradient(circle at 48% 117%, #899aae00 29.65%, #65c363 29% 35.4%, #576d8200 25%), linear-gradient(321deg, #0000 45.4%, #576d82 22%), linear-gradient(339deg, #0000 39.4%, #576d82 22%), linear-gradient(360deg, #899aae00 25%, #65c363 25% 33%, #576d8200 33%), #899aae",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-903": {
        "background": "#36AFE6"
    },
    "livery-906": {
        "background": "linear-gradient(to top, #cc181a 34%, #da271e 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-907": {
        "background": "linear-gradient(to top, #f15325 25%, #fff 25%)"
    },
    "livery-909": {
        "background": "linear-gradient(to top, #6b767c 34%, #43cff6 34%, #43cff6 67%, #6b767c 67%)"
    },
    "livery-910": {
        "background": "radial-gradient(at -20% 460%, #2430 93%, #f6e72d 93%), radial-gradient(at 0% -80%, #0E4194 80%, #f6e72d 80%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#243784"
    },
    "livery-911": {
        "background": "linear-gradient(300deg, #0000 72%, #0e62ac 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#ffffff"
    },
    "livery-913": {
        "background": "linear-gradient(to right, #ef59a5 28%, #fdcc0d 28%, #fdcc0d 37%, #00adf2 37%, #00adf2 46%, #00467c 46%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-915": {
        "background": "linear-gradient(to top, #007f7e 25%, #ffffff 25%)"
    },
    "livery-917": {
        "stroke": "#ebf1fd",
        "background": "linear-gradient(300deg, #0000 72%, #3bc7cc 20%), linear-gradient(300deg, #004c1e 28%, #0000 28%), linear-gradient(#0000 85%, #ebf1fd 85%), linear-gradient(300deg, #0000 31%, #3f8b4a 31% 39%, #0000 39%), #ebf1fd"
    },
    "livery-952": {
        "background": "#737c82",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-953": {
        "background": "linear-gradient(110deg, #bb3e81 55%, #e57aa7 55%, #e57aa7 64%, #fff 64%, #fff 73%, #6c1256 73%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#bb3e81"
    },
    "livery-954": {
        "background": "linear-gradient(100deg, #A60E14 25%, #EDF0F5 25%, #EDF0F5 35%, transparent 30%), linear-gradient(to top, #495058 25%, #C5C5C5 25%)",
        "stroke": "#c5c5c5"
    },
    "livery-955": {
        "background": "radial-gradient(circle at -10% -73%, #fff0 76%, #025 76%), radial-gradient(circle at -45% -83%, #dee 76%, #6e5 76%)",
        "stroke": "#ddeeee"
    },
    "livery-958": {
        "background": "linear-gradient(to top, #273885 12%, #fff 12%, #fff 23%, #d7b957 23%, #d7b957 34%, #fff 34%)"
    },
    "livery-960": {
        "background": "linear-gradient(300deg, #0000 72%, #bf4086 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-961": {
        "background": "radial-gradient(ellipse at bottom left, transparent 20%, #fff 20%, #fff 40%, transparent 40%), linear-gradient(to top, #b32531 20%, #fff 20%, #fff 80%, #b32531 80%)"
    },
    "livery-962": {
        "background": "linear-gradient(to top, #CA0086 50%, #8C006A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-965": {
        "background": "linear-gradient(60deg, transparent 65%, #fff 65%, #fff 70%, transparent 70%), linear-gradient(110deg, transparent 70%, #302661 70%), linear-gradient(60deg, transparent 65%, #493c8f 65%), linear-gradient(to top, #eed878 20%, #cba85f 20%)",
        "stroke": "#eed878"
    },
    "livery-966": {
        "background": "#10ab74",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-967": {
        "background": "linear-gradient(100deg, #01aadb 34%, #193276 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1000": {
        "background": "linear-gradient(100deg, #55c232 60%, #fff 60%, #fff 70%, #1c559c 70%)"
    },
    "livery-1001": {
        "background": "linear-gradient(110deg, #fe92af 55%, #fea2d5 55%, #fea2d5 64%, #ffffff 64%, #ffffff 73%, #2c8cff 73%)"
    },
    "livery-1002": {
        "background": "linear-gradient(110deg, #f6941d 55%, #e08900 55%, #e08900 64%, #ffffff 64%, #ffffff 73%, #ad1b11 73%)",
        "stroke": "#f6941d"
    },
    "livery-1003": {
        "background": "linear-gradient(to top, #272723 50%, #fee49b 50%)",
        "stroke": "#FFFFFF"
    },
    "livery-1004": {
        "background": "linear-gradient(to top, #0a3069 25%, #fdeda7 25%, #fdeda7 50%, #71bdd1 50%, #71bdd1 75%, #fdeda7 75%)",
        "stroke": "#ffffff"
    },
    "livery-1005": {
        "background": "linear-gradient(to top, #0c3662 20%, #B0BAC4 20%, #B0BAC4 27%, #39B7FF 27%, #39B7FF 47%, #0c3662 47%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#0c3662"
    },
    "livery-1006": {
        "background": "linear-gradient(to top, #1e409a 28%, #ffffff 28%, #ffffff 37%, #a0c6e9 37%, #a0c6e9 46%, #ffffff 46%)"
    },
    "livery-1007": {
        "background": "repeating-conic-gradient(from 90deg at 59% 100%, #0000 0deg 124deg, #052 122deg 132deg, #083 132deg 180deg), linear-gradient(113deg, #0000 68%, #cd0 66%, #cd0 74%, #0000 74%), repeating-conic-gradient(from 90deg at 65% 100%, #9c2 0deg 55deg, #ff0 55deg 112deg, #cd0 112deg 180deg)",
        "stroke": "#99cc22"
    },
    "livery-1008": {
        "background": "#ed1d25",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1009": {
        "background": "linear-gradient(to top, #46648e 28%, #edebd4 28%, #edebd4 55%, #46648e 55%, #46648e 64%, #edebd4 64%, #edebd4 82%, #46648e 82%)",
        "stroke": "#ffffff"
    },
    "livery-1011": {
        "background": "linear-gradient(300deg, #0000 72%, #00dcff 20%), linear-gradient(300deg, #2d3677 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #66aafd 31%, #66aafd 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-1012": {
        "background": "linear-gradient(300deg, #0000 72%, #60d74f 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-1013": {
        "background": "linear-gradient(to top, #ffffff 7%, #0F6DB4 7%, #0F6DB4 17%, #ffffff 17%, #ffffff 20%, #EA2639 20%, #EA2639 30%, #ffffff 30%, #ffffff 33%, #F79F48 33%, #F79F48 42%, #ffffff 42%)",
        "stroke": "#ffffff"
    },
    "livery-1015": {
        "background": "linear-gradient(135deg, #fbe538 34%, #008734 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1016": {
        "background": "linear-gradient(to top, #b51a00 10%, #B89366 10%, #B89366 15%, #b51a00 15%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1017": {
        "background": "#6fccfa"
    },
    "livery-1018": {
        "background": "linear-gradient(300deg, #004b2a 28%, #0000 28%), linear-gradient(to top, #8d3 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #e7d200 31%, #e7d200 39%, #0000 39%), linear-gradient(to top, #8d3 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #1e9b19 20%), #8d3",
        "stroke": "#7ed02d"
    },
    "livery-1019": {
        "background": "linear-gradient(120deg, #82E06C 29%, #212D5D 29%, #212D5D 72%, #48A3D8 72%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1020": {
        "background": "linear-gradient(105deg, #8be35f 20%, #fff 17%)"
    },
    "livery-1021": {
        "background": "linear-gradient(145deg, #52d6fc 40%, #1e325f 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1022": {
        "background": "linear-gradient(to right, #f5bc25 50%, #592b7a 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#592b7a"
    },
    "livery-1023": {
        "background": "linear-gradient(to top, #377e5f 34%, #4b9f29 34%, #4b9f29 67%, #6ee7ff 67%)"
    },
    "livery-1024": {
        "background": "linear-gradient(to top, #be7454 15%, #f8f3e7 15%, #f8f3e7 86%, #be7454 86%)"
    },
    "livery-1025": {
        "background": "linear-gradient(300deg, #0000 72%, #0087bf 20%), linear-gradient(300deg, #1d5e86 28%, #0000 28%), linear-gradient(to top, #0087bf 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #5dcaff 31%, #5dcaff 39%, #0000 39%), #0087bf",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1026": {
        "background": "linear-gradient(to top, #dc241f 34%, #ebf1f1 34%, #ebf1f1 67%, #dc241f 67%)"
    },
    "livery-1027": {
        "background": "linear-gradient(300deg, #0000 72%, #bbceed 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-1028": {
        "background": "#d92c1f",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1029": {
        "background": "linear-gradient(to right, #a2eb0e 45%, #018e3a 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#115544"
    },
    "livery-1030": {
        "background": "#cf162d",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1031": {
        "background": "linear-gradient(115deg, #46ab18 58%, #ba1111 58%, #ba1111 72%, #23421b 72%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1032": {
        "background": "linear-gradient(300deg, #0000 72%, #0087bf 20%), linear-gradient(300deg, #012e73 28%, #0000 28%), linear-gradient(to top, #0087bf 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #fbde19 31%, #fbde19 39%, #0000 39%), #0087bf",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#0087bf"
    },
    "livery-1033": {
        "background": "#27a0df",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1034": {
        "background": "linear-gradient(to top, #dc241f 25%, #ffffff 25%, #ffffff 50%, #dc241f 50%, #dc241f 75%, #ffffff 75%)",
        "stroke": "#ffffff"
    },
    "livery-1035": {
        "background": "linear-gradient(to top, #fffcd6 34%, #dc241f 34%, #dc241f 67%, #fffcd6 67%)"
    },
    "livery-1037": {
        "background": "radial-gradient(circle at 54% 46%, #301 49%, #fff0 49%), radial-gradient(circle at 50% 50%, #f8a 56%, #fff0 56%), linear-gradient(90deg, #712 50%, #301 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1038": {
        "background": "linear-gradient(to left, #09514b 50%, transparent 50%), radial-gradient(circle at center, #09514b 58%, #5ac4ad 58%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1041": {
        "background": "linear-gradient(to left, #f42 50%, transparent 50%), radial-gradient(circle at center, #f42 58%, #f91 58%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1044": {
        "background": "conic-gradient(from 270deg at 99.4% 42%, #0b1f68 90deg, #0000 90deg), radial-gradient(at 35% 177%, #5199f3 39%, transparent 31%), radial-gradient(at 31% 176%, #bae3fb 39%, transparent 31%), conic-gradient(from 188deg, #0b1f68 180deg, #0000 180deg), radial-gradient(circle at 64.4% 39.5%, #0b1f68 46%, #152c2a00 31%), radial-gradient(circle at 66.8% 46%, #bae3fb 43%, #5199f3 31%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1045": {
        "background": "#F9F923"
    },
    "livery-1049": {
        "background": "linear-gradient(135deg, #fded9a 50%, #ef6909 50%)"
    },
    "livery-1052": {
        "background": "linear-gradient(300deg, #0000 72%, #009eda 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-1055": {
        "background": "#669d34",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1057": {
        "background": "linear-gradient(300deg, #0000 72%, #ed1d23 20%), linear-gradient(300deg, #8b001d 28%, #0000 28%), linear-gradient(to top, #ed1d23 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #f7941e 31%, #f7941e 39%, #0000 39%), #ed1d23",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1059": {
        "background": "linear-gradient(to top, #02034e 25%, #f5f39a 25%)",
        "stroke": "#f5f39a"
    },
    "livery-1060": {
        "background": "linear-gradient(to top, #ea1a18 50%, #fbfffc 50%)"
    },
    "livery-1061": {
        "background": "linear-gradient(to top, #02034e 25%, #f5f39a 25%, #f5f39a 50%, #02034e 50%, #02034e 75%, #f5f39a 75%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#02034e"
    },
    "livery-1063": {
        "background": "linear-gradient(to top, #00deff 50%, #ffffff 50%)"
    },
    "livery-1064": {
        "background": "radial-gradient(circle at top, #FF6416 50%, #464644 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1065": {
        "background": "radial-gradient(ellipse at top left, #1c6325 25%, #6ad52c 15% 27%, #0000 15%), linear-gradient(to top, #1c6325 15%, #1c60 15%), linear-gradient(352deg, #1c6325 23.4%, #1c60 15%), linear-gradient(346deg, #1c6325 27.22%, #1c60 15%), linear-gradient(to top, #6ad52c 18%, #1c60 15%), linear-gradient(to right, #eee4d7 34%, #0000 20%), radial-gradient(circle at 33% 0%, #eee4d7 58%, #6ad52c 58% 60%, #1c6325 22%)"
    },
    "livery-1068": {
        "background": "linear-gradient(to top, #49baff 50%, #fff 50%)"
    },
    "livery-1070": {
        "background": "repeating-conic-gradient(from 227deg at 78% 97%, #0000 0deg 90deg, #fff 90deg 95deg, #fff0 95deg 97deg, #fff 97deg 102deg, #0000 102deg 360deg), linear-gradient(235deg, #f18602 45%, #1da6c2 45%)"
    },
    "livery-1071": {
        "background": "linear-gradient(110deg, #d71921 55%, #f6611d 55%, #f6611d 64%, #fff 64%, #fff 73%, #790013 73%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#D71921"
    },
    "livery-1073": {
        "background": "linear-gradient(to top, #3f4073 19%, #AB985A 19%, #AB985A 28%, #758CFE 28%, #758CFE 46%, #464FB8 46%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1074": {
        "background": "linear-gradient(to bottom, #4d8cdc 70%, #d5d3d3 70%, #d5d3d3 75%, #4d8cdc 75%, #4d8cdc 80%, #d5d3d3 80%, #d5d3d3 85%, #4d8cdc 85%, #4d8cdc 90%, #d5d3d3 90%, #d5d3d3 95%, #4d8cdc 95%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1075": {
        "background": "linear-gradient(300deg, #315b35 28%, #0000 28%), linear-gradient(to top, #71bc0b 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #eae9a9 31%, #eae9a9 39%, #0000 39%), linear-gradient(to top, #71bc0b 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #eae9a9 20%), #71bc0b",
        "stroke": "#FFFFFF"
    },
    "livery-1076": {
        "background": "radial-gradient(circle at 46.5% 45%, #360838 25%, transparent 25.5%), linear-gradient(70deg, #fff 37%, transparent 37%), linear-gradient(115deg, #fff 32%, transparent 32.5%), linear-gradient(21deg, #fff 35%, #360838 35.5%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#380b37"
    },
    "livery-1077": {
        "background": "linear-gradient(to right, #c5c4c0 34%, #b46b29 34%, #b46b29 42%, #9d1f1d 42%, #9d1f1d 50%, #275d7b 50%, #275d7b 59%, #062a63 59%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1078": {
        "background": "repeating-conic-gradient(from 227deg at 78% 97%, #0000 0deg 90deg, #fff 90deg 95deg, #fff0 95deg 97deg, #fff 97deg 102deg, #0000 102deg 360deg), linear-gradient(235deg, #e41 45%, #f90 45%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#ee4411"
    },
    "livery-1080": {
        "background": "linear-gradient(300deg, #173 28%, #0000 28%), linear-gradient(to top, #8f5 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #f00 31%, #f00 39%, #0000 39%), linear-gradient(to top, #8f5 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #f00 20%), #8f5",
        "stroke": "#88ff55"
    },
    "livery-1081": {
        "background": "linear-gradient(to bottom, #FDC52E 70%, transparent 70%), linear-gradient(120deg, #c00000 40%, #FDC52E 40%, #FDC52E 60%, #c00000 60%)",
        "stroke": "#FDC52E"
    },
    "livery-1082": {
        "background": "linear-gradient(135deg, #ff63a0 34%, #ff0078 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1084": {
        "background": "linear-gradient(135deg, #86BCEA 34%, #F8C327 34%, #F8C327 50%, #2A4177 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#2A4177"
    },
    "livery-1085": {
        "background": "linear-gradient(to right, #6d1d2b 38%, #fff 38%, #fff 50%, #d40915 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#d40915"
    },
    "livery-1087": {
        "background": "linear-gradient(to top, #808080 75%, #fc3503 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1088": {
        "background": "linear-gradient(to top, #fe482b 50%, #e1e4e8 50%)"
    },
    "livery-1089": {
        "background": "radial-gradient(ellipse at 20% 134%, #00A0BE 30%, transparent 30%), radial-gradient(ellipse at 51% 16%, #23294F 60%, transparent 0%), linear-gradient(80deg, #23294F 0%, #23294F 31%, transparent 10%), radial-gradient(circle at 58% 16%, #B3B3B3 0%, #B3B3B3 50%, transparent 20%), radial-gradient(ellipse at 50% 16%, #23294F 60%, transparent 10%), radial-gradient(ellipse at 50% 16%, #00A0BE 60%, #00A0BE 0%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1090": {
        "background": "linear-gradient(110deg, #c3a6ea 55%, #f8942f 55%, #f8942f 64%, #ffffff 64%, #ffffff 73%, #3e2b7e 73%)",
        "stroke": "#c3a6ea"
    },
    "livery-1091": {
        "background": "linear-gradient(110deg, #f9f387 25%, #5862b9 25%, #5862b9 50%, #6cc5ff 50%, #6cc5ff 75%, #df6891 75%)"
    },
    "livery-1092": {
        "background": "linear-gradient(110deg, #9cb5e6 55%, #78bad8 55%, #78bad8 64%, #fff 64%, #fff 73%, #01226a 73%)",
        "stroke": "#9cb5e6"
    },
    "livery-1095": {
        "background": "linear-gradient(110deg, #8b106a 55%, #dc64a2 55%, #dc64a2 64%, #fff 64%, #fff 73%, #e40513 73%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#8b106a"
    },
    "livery-1098": {
        "background": "linear-gradient(110deg, #fff 70%, #9987d9 70%, #9987d9 75%, #614d9b 75%)"
    },
    "livery-1099": {
        "background": "radial-gradient(ellipse at 20% 134%, #D81E29 30%, transparent 30%), radial-gradient(ellipse at 51% 16%, #23294F 60%, transparent 0%), linear-gradient(80deg, #23294F 0%, #23294F 31%, transparent 10%), radial-gradient(circle at 58% 16%, #B3B3B3 0%, #B3B3B3 50%, transparent 20%), radial-gradient(ellipse at 50% 16%, #23294F 60%, transparent 10%), radial-gradient(ellipse at 50% 16%, #D81E29 60%, #D81E29 0%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1100": {
        "background": "radial-gradient(ellipse at 20% 134%, #FEC31E 30%, transparent 30%), radial-gradient(ellipse at 51% 16%, #23294F 60%, transparent 0%), linear-gradient(80deg, #23294F 0%, #23294F 31%, transparent 10%), radial-gradient(circle at 58% 16%, #B3B3B3 0%, #B3B3B3 50%, transparent 20%), radial-gradient(ellipse at 50% 16%, #23294F 60%, transparent 10%), radial-gradient(ellipse at 50% 16%, #FEC31E 60%, #FEC31E 0%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#23294F"
    },
    "livery-1101": {
        "background": "linear-gradient(to right, #79933a 13%, #fff 13%, #fff 63%, #79933a 63%, #79933a 75%, #fff 75%, #fff 88%, #79933a 88%)"
    },
    "livery-1104": {
        "background": "linear-gradient(110deg, #1D98ED 55%, #4DD7F9 55%, #4DD7F9 64%, #ffffff 64%, #ffffff 73%, #203B87 73%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#1D98ED"
    },
    "livery-1105": {
        "background": "linear-gradient(to right, #bb261a 50%, #75150c 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1106": {
        "background": "linear-gradient(110deg, #e8ca7f 55%, #764527 55%, #764527 64%, #fff 64%, #fff 73%, #764527 73%)",
        "stroke": "#e8ca7f"
    },
    "livery-1107": {
        "background": "#ffff00"
    },
    "livery-1144": {
        "background": "linear-gradient(to top, #c31e19 25%, #ffe7a7 25%)"
    },
    "livery-1145": {
        "background": "linear-gradient(110deg, #abfc96 55%, #5db132 55%, #5db132 64%, #fff 64%, #fff 73%, #004884 73%)",
        "stroke": "#abfc96"
    },
    "livery-1146": {
        "background": "#8b9eaf"
    },
    "livery-1148": {
        "background": "linear-gradient(to top, #46c2a0 38%, #eef0e1 38%, #eef0e1 50%, #46c2a0 50%)"
    },
    "livery-1149": {
        "background": "linear-gradient(110deg, #373634 55%, #e84e10 55%, #e84e10 64%, #fff 64%, #fff 73%, #e10712 73%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#373634"
    },
    "livery-1154": {
        "background": "linear-gradient(110deg, #b21917 55%, #f4bb5b 55%, #f4bb5b 64%, #fff 64%, #fff 73%, #c3af79 73%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#B21917"
    },
    "livery-1155": {
        "background": "linear-gradient(120deg, #e2c430 28%, #67b643 28%, #67b643 34%, #3c75d1 34%, #3c75d1 39%, #6e3697 39%, #6e3697 45%, #000 45%, #000 50%, #4d2929 50%, #4d2929 56%, #5197ca 56%, #5197ca 62%, #ca56a1 62%, #ca56a1 67%, #fff 67%, #fff 73%, #c00067 73%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1156": {
        "background": "linear-gradient(110deg, #bebcbc 55%, #e20a17 55%, #e20a17 64%, #fff 64%, #fff 73%, #e20a17 73%)",
        "stroke": "#BEBCBC"
    },
    "livery-1157": {
        "background": "linear-gradient(110deg, #8fbf21 55%, #fffb43 55%, #fffb43 64%, #fff 64%, #fff 73%, #006533 73%)",
        "stroke": "#8FBF21"
    },
    "livery-1158": {
        "background": "linear-gradient(300deg, #0000 72%, #072891 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#ebf1fd"
    },
    "livery-1159": {
        "background": "linear-gradient(50deg, #F18700 52%, #fff 60%, #717171 68%)"
    },
    "livery-1160": {
        "background": "repeating-conic-gradient(from 227deg at 78% 97%, #0000 0deg 90deg, #fff 90deg 95deg, #fff0 95deg 97deg, #fff 97deg 102deg, #0000 102deg 360deg), linear-gradient(235deg, #F18700 45%, #AC9ECA 45%)"
    },
    "livery-1163": {
        "background": "linear-gradient(to top, #1c2b64 17.5%, transparent 17.5%), radial-gradient(circle at 90% 140%, #0c9c6b 41%, #fff 41.5%, #fff 43.5%, transparent 44%), radial-gradient(circle at 135% 74%, #92bfe9 45%, transparent 45.5%), linear-gradient(90deg, #fff 0%, #fff 100%)",
        "stroke": "#ffffff"
    },
    "livery-1164": {
        "background": "repeating-conic-gradient(from 227deg at 78% 97%, #0000 0deg 90deg, #fff 90deg 95deg, #fff0 95deg 97deg, #fff 97deg 102deg, #0000 102deg 360deg), linear-gradient(235deg, #C8421B 45%, #42388a 45%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#C8421B"
    },
    "livery-1166": {
        "background": "#0055A5",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1167": {
        "background": "linear-gradient(130deg, #4dd937 50%, #00501f 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1168": {
        "background": "linear-gradient(300deg, #0000 72%, #000 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #ebf1fd 31%, #a9b8e3 31%, #a9b8e3 39%, #ebf1fd 39%)"
    },
    "livery-1169": {
        "background": "radial-gradient(circle at left 45%, #cd3 35%, #0a4 45%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#00aa44"
    },
    "livery-1170": {
        "background": "radial-gradient(circle at left 45%, #A13005 35%, #0000 40%), radial-gradient(circle at 85% 163%, #BF0413 40%, #5B010A 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1171": {
        "background": "linear-gradient(90deg, #f30 45%, #0000 45%, #0000 55%, #333 55%), linear-gradient(180deg, #e02 85%, #333 85%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1175": {
        "background": "#97B732"
    },
    "livery-1176": {
        "background": "#429194",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1178": {
        "background": "linear-gradient(135deg, #FFF8B2 34%, #881726 34%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#881726"
    },
    "livery-1179": {
        "background": "#A3191F",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1181": {
        "background": "#A3191F",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1182": {
        "background": "#373536",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1183": {
        "color": "#fff",
        "fill": "#fff",
        "background": "radial-gradient(circle at -10% -73%, #808083 76%, #88d3ff 76% 81%, #0f358d 81%)"
    },
    "livery-1184": {
        "background": "#97B732",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1185": {
        "background": "#fd6000",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1187": {
        "background": "#A3191F",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1188": {
        "background": "#47C032"
    },
    "livery-1189": {
        "background": "#A3191F",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1191": {
        "background": "#A82C71",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1192": {
        "background": "linear-gradient(to top, #0e5d78 25%, #00afc5 25%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1193": {
        "background": "linear-gradient(to top, #F2C701 34%, #F95D2C 34%, #F95D2C 67%, #F2C701 67%)"
    },
    "livery-1194": {
        "background": "radial-gradient(circle at left 45%, #65c658 35%, #fff 45%)"
    },
    "livery-1195": {
        "background": "radial-gradient(circle at left 45%, #D5CAB7 35%, #F94471 45%)"
    },
    "livery-1196": {
        "background": "radial-gradient(circle at left 45%, #65c658 35%, #fff 45%)"
    },
    "livery-1199": {
        "background": "linear-gradient(300deg, #6f0910 28%, #0000 28%), linear-gradient(to top, #f2b715 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #ce1e21 31%, #ce1e21 39%, #0000 39%), linear-gradient(to top, #f2b715 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #ce1e21 20%), #f2b715",
        "color": "#6f0910",
        "fill": "#6f0910",
        "stroke": "#f2b715"
    },
    "livery-1200": {
        "background": "linear-gradient(to top, #01449A 25%, #82DD40 25%)"
    },
    "livery-1201": {
        "background": "#621922",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1202": {
        "background": "repeating-conic-gradient(from 90deg at 59% 100%, #0000 0deg 124deg, #024 122deg 132deg, #08d 132deg 180deg), linear-gradient(113deg, #0000 68%, #ff0 66%, #ff0 74%, #0000 74%), repeating-conic-gradient(from 90deg at 65% 100%, #0bf 0deg 55deg, #8df 55deg 112deg, #ff0 112deg 180deg)",
        "stroke": "#82d0f5"
    },
    "livery-1235": {
        "background": "linear-gradient(125deg, #9ee03b 50%, #2f7185 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1236": {
        "background": "repeating-conic-gradient(from 227deg at 78% 97%, #0000 0deg 90deg, #fff 90deg 95deg, #fff0 95deg 97deg, #fff 97deg 102deg, #0000 102deg 360deg), linear-gradient(235deg, #C8421B 45%, #5abf4e 45%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#C8421B"
    },
    "livery-1237": {
        "background": "linear-gradient(65deg, #008bd2 30%, transparent 30%), linear-gradient(115deg, #008bd2 30%, #000 30%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1238": {
        "background": "linear-gradient(to right, #ffffff 43%, #d79458 43%, #d79458 58%, #020066 58%)",
        "stroke": "#ffffff"
    },
    "livery-1239": {
        "background": "#FFE7C0"
    },
    "livery-1241": {
        "background": "linear-gradient(to top, #9c0840 25%, #f4edd2 25%, #f4edd2 50%, #9c0840 50%)",
        "color": "#f4edd2",
        "fill": "#f4edd2",
        "stroke": "#9c0840"
    },
    "livery-1243": {
        "background": "linear-gradient(to top, #00dc35 34%, #afe3fb 34%)"
    },
    "livery-1244": {
        "background": "linear-gradient(to top, #fff 50%, #41a9e0 50%)",
        "stroke": "#ffffff"
    },
    "livery-1246": {
        "background": "linear-gradient(300deg, #0000 72%, #ebf1fd 20%), linear-gradient(300deg, #2d3677 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #66aafd 31%, #66aafd 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-1249": {
        "background": "linear-gradient(300deg, #0f65b0 28%, #0000 28%), linear-gradient(to top, #ffeb72 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #1cb8eb 31%, #1cb8eb 39%, #0000 39%), linear-gradient(to top, #ffeb72 54%, #0000 50%), linear-gradient(300deg, #0000 77%, #ffd307 77%, #ffd307 81%, #72ccf1 81%), #ffeb72",
        "stroke": "#ffeb72"
    },
    "livery-1250": {
        "background": "linear-gradient(to top, #3a4492 25%, #fff 25%)"
    },
    "livery-1252": {
        "background": "linear-gradient(300deg, #236 28%, #0000 28%), linear-gradient(to top, #cee 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #cee 31%, #cee 39%, #0000 39%), linear-gradient(to top, #cee 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #236 20%), #cee",
        "stroke": "#c1dce7"
    },
    "livery-1254": {
        "background": "linear-gradient(300deg, #004d22 28%, #0000 28%), linear-gradient(to top, #ffc500 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #f0340f 31%, #f0340f 39%, #0000 39%), #ffc500"
    },
    "livery-1256": {
        "background": "linear-gradient(to right, #ffc406 30%, #0092e9 30%, #0092e9 60%, #245675 60%, #245675 90%, #ff7b08 90%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1258": {
        "background": "radial-gradient(circle at left 45%, #3bc 35%, #077 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1262": {
        "background": "linear-gradient(to right, transparent 60%, #126 90%), linear-gradient(to top, #a27 20%, #c7a 20%, #c7a 30%, #5bf 30%, #5bf 40%, #643 40%, #643 50%, #126 50%, #126 60%, #084 60%, #084 70%, #cc0 70%, #cc0 80%, #b52 80%, #b52 90%, #a02 90%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#112266"
    },
    "livery-1266": {
        "background": "linear-gradient(300deg, #0000 72%, #59bd49 20%), linear-gradient(300deg, #004c1e 28%, #0000 28%), linear-gradient(to top, #59bd49 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #439939 31%, #439939 39%, #0000 39%), #59bd49",
        "stroke": "#59bd49"
    },
    "livery-1267": {
        "background": "linear-gradient(60deg, #74d547 35%, #d3d3d3 35%, #d3d3d3 39%, #fff 39%, #fff 43%, #74d547 43%, #74d547 47%, #000 47%)",
        "color": "#ffffff",
        "fill": "#ffffff",
        "stroke": "#000000"
    },
    "livery-1268": {
        "background": "linear-gradient(to right, #9b2b31 13%, #f6ecb7 13%, #f6ecb7 63%, #9b2b31 63%, #9b2b31 75%, #f6ecb7 75%, #f6ecb7 88%, #9b2b31 88%)",
        "color": "#9b2b31",
        "fill": "#9b2b31",
        "stroke": "#f6ecb7"
    },
    "livery-1269": {
        "background": "linear-gradient(to right, #b41c00 50%, #dfd4a7 50%, #dfd4a7 67%, #b41c00 67%, #b41c00 84%, #dfd4a7 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1270": {
        "background": "linear-gradient(300deg, #0000 72%, #88929b 20%), linear-gradient(300deg, #2d2f30 28%, #0000 28%), linear-gradient(to top, #afb6c0 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #cca75b 31%, #c01f39 33%, #3ba1e2 35%, #d26e43 37%, #552c62 39%, #0000 39%), #afb6c0"
    },
    "livery-1272": {
        "background": "linear-gradient(300deg, #0000 72%, #fee46d 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-1275": {
        "background": "linear-gradient(300deg, #0000 72%, #cf4a9a 20%), linear-gradient(300deg, #760051 28%, #0000 28%), linear-gradient(to top, #cf4a9a 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #f390bc 31%, #f390bc 39%, #0000 39%), #cf4a9a",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1277": {
        "background": "linear-gradient(300deg, #0000 72%, #afb6c0 20%), linear-gradient(300deg, #2d2f30 28%, #0000 28%), linear-gradient(to top, #afb6c0 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #cca75b 31%, #c01f39 33%, #3ba1e2 35%, #d26e43 37%, #552c62 39%, #0000 39%), #afb6c0",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1278": {
        "background": "linear-gradient(300deg, #0000 72%, #f08a01 20%), linear-gradient(300deg, #ed5100 28%, #0000 28%), linear-gradient(to top, #f8bf00 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #f08a01 31%, #f08a01 39%, #0000 39%), #f8bf00"
    },
    "livery-1281": {
        "background": "linear-gradient(to top, #520e14 20%, #ebb730 20%, #ebb730 25%, #dc241f 25%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1286": {
        "background": "linear-gradient(300deg, #0000 72%, #bbceed 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-1287": {
        "background": "linear-gradient(120deg, #fb83ab 60%, #d14d80 60%, #d14d80 80%, #fb83ab 80%)"
    },
    "livery-1288": {
        "background": "linear-gradient(270deg, #0000 95%, #1A2F80 5%), linear-gradient(90deg, #0000 95%, #1A2F80 5%), #ffff00"
    },
    "livery-1289": {
        "background": "linear-gradient(45deg, #314e87 41%, #3c75d1 41%, #3c75d1 44%, #314e87 44%, #314e87 47%, #6e3697 47%, #6e3697 50%, #3c75d1 50%, #3c75d1 54%, #67b643 54%, #67b643 57%, #e2c430 57%, #e2c430 60%, #ec9629 60%, #ec9629 63%, #db3a31 63%, #db3a31 66%, #314e87 66%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1290": {
        "background": "linear-gradient(to left, #ff4 50%, transparent 50%), radial-gradient(circle at center, #ff4 58%, #fc0 58%)"
    },
    "livery-1292": {
        "background": "linear-gradient(to top, #e7292d 23%, #a9599c 23%, #a9599c 34%, #e7292d 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1293": {
        "background": "linear-gradient(to left, #a01080 50%, transparent 50%), radial-gradient(circle at center, #a01080 58%, #cc33aa 58%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1294": {
        "background": "radial-gradient(ellipse 36% 53% at 47% 35%, #fff 90%, #0000 90%), radial-gradient(ellipse 35% 53% at 55% 30%, #000 100%, #0000 100%), linear-gradient(180deg, #0000 83%, #e22 83%), linear-gradient(270deg, #e22 50%, #fff 50%)"
    },
    "livery-1296": {
        "background": "linear-gradient(300deg, #0000 72%, #ffc406 20%), linear-gradient(300deg, #f6672a 28%, #0000 28%), linear-gradient(to top, #ffc406 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #ee1e21 31%, #ee1e21 39%, #0000 39%), #ffc406",
        "stroke": "#ffc406"
    },
    "livery-1297": {
        "background": "linear-gradient(to left, #ee0000 50%, transparent 50%), radial-gradient(circle at center, #ee0000 58%, #aa0000 58%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1299": {
        "background": "radial-gradient(circle at 54% 46%, #fa1 49%, #fff0 49%), radial-gradient(circle at 50% 50%, #ec8 56%, #fff0 56%), linear-gradient(90deg, #f42 50%, #fa1 50%)"
    },
    "livery-1300": {
        "background": "linear-gradient(to top, #ffffff 9%, #F2B90C 9%, #F2B90C 17%, #ffffff 17%, #ffffff 25%, #A8BF54 25%, #A8BF54 34%, #ffffff 34%, #ffffff 42%, #035939 42%, #035939 50%, #ffffff 50%)",
        "stroke": "#ffffff"
    },
    "livery-1301": {
        "background": "linear-gradient(to top, #64ab69 15%, #fff 15%, #fff 20%, #009593 20%, #009593 55%, #fff 55%, #fff 60%, #006696 60%, #006696 95%, #fff 95%, #fff 100%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#006696"
    },
    "livery-1303": {
        "background": "linear-gradient(to right, #11349c 50%, #fff 50%, #fff 75%, #11349c 75%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#11349c"
    },
    "livery-1305": {
        "background": "linear-gradient(135deg, #ff0000 25%, #add8e6 25%, #add8e6 50%, #ffae42 50%, #ffae42 75%, #cc8899 75%)",
        "stroke": "#add8e6"
    },
    "livery-1306": {
        "background": "radial-gradient(circle at top, #f02826 50%, #611618 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1307": {
        "background": "linear-gradient(to right, #471d19 8%, #efbe55 8%, #efbe55 31%, #ac7853 31%, #ac7853 39%, #efbe55 39%, #efbe55 77%, #73533b 77%, #73533b 85%, #471d19 85%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#471d19"
    },
    "livery-1308": {
        "background": "linear-gradient(300deg, #0000 72%, #02943f 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-1309": {
        "background": "#FF0000",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1310": {
        "background": "linear-gradient(to top, #01205e 25%, #fff 25%, #fff 35%, #12799a 35%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#12799a"
    },
    "livery-1311": {
        "background": "radial-gradient(circle at -20% 25%, #b632c0 48%, #eec750 48%, #eec750 56%, #A5A5A5 56%, #A5A5A5 62%, #25B0CF 62%)"
    },
    "livery-1312": {
        "background": "linear-gradient(300deg, #0088aa 28%, #0000 28%), linear-gradient(to top, #ffee66 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #ee1111 31%, #ee1111 39%, #0000 39%), linear-gradient(to top, #ffee66 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #55bbdd 20%), #fe6",
        "stroke": "#ffee66"
    },
    "livery-1318": {
        "background": "linear-gradient(285deg, #ED1B23 60%, #7C777B 60%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#ED1B23"
    },
    "livery-1319": {
        "background": "linear-gradient(120deg, #053F72 29%, #C0C0C0 29%, #C0C0C0 72%, #5D1B75 72%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-1322": {
        "background": "radial-gradient(circle at 25% 25%, #0000 50.5%, #898886 51% 62%, #0000 62.5%), radial-gradient(circle at 29% 33%, #898886 62%, #0000 62.5%), radial-gradient(circle at 29% 36%, #0000 50.5%, #898886 51% 62%, #0000 62.5%), radial-gradient(circle at 20% 35%, #0000 50.5%, #898886 51% 62%, #0000 62.5%), radial-gradient(circle at top left, #0000 64.5%, #acacac 65% 77%, #393939 77.5%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-1323": {
        "background": "linear-gradient(300deg, #0000 72%, #9e9e9e 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-1325": {
        "background": "linear-gradient(to top, #3e3e3e 25%, #a09d95 25%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1326": {
        "background": "linear-gradient(300deg, #0000 72%, #05A7FF 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-1327": {
        "background": "linear-gradient(to top, #FF0000 40%, #fff1e0 40%, #fff1e0 60%, #FF0000 60%)",
        "stroke": "#fff1e0"
    },
    "livery-1328": {
        "background": "linear-gradient(110deg, transparent 84%, #fff1e0 84%), linear-gradient(to top, #203777 15%, transparent 15%), linear-gradient(110deg, transparent 60%, #FFC73A 60%, #FFC73A 72%, #203777 72%, #203777 84%, #fff1e0 84%), linear-gradient(to top, #203777 15%, #FFC73A 15%, #FFC73A 30%, #fff1e0 30%)",
        "stroke": "#fff1e0"
    },
    "livery-1331": {
        "background": "linear-gradient(to top, #000 10%, #dc241f 10%, #dc241f 30%, #fad785 30%, #fad785 50%, #dc241f 50%, #dc241f 70%, #fad785 70%, #fad785 90%, #738183 90%)",
        "stroke": "#fad785"
    },
    "livery-1332": {
        "background": "linear-gradient(300deg, #ff7518 28%, #0000 28%), linear-gradient(to top, #ffff00 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #ffb347 31%, #ffb347 39%, #0000 39%), #ffff00",
        "stroke": "#ffff00"
    },
    "livery-1333": {
        "background": "linear-gradient(to top, #004488 43%, #0088ff 43%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1334": {
        "background": "linear-gradient(64deg, #6ebdff 49%, #263162 49%, #263162 52%, #6ebdff 52%, #6ebdff 56%, #263162 56%, #263162 60%, #6ebdff 60%, #6ebdff 63%, #263162 63%, #263162 67%, #6ebdff 67%, #6ebdff 71%, #263162 71%)",
        "stroke": "#6ebdff"
    },
    "livery-1335": {
        "background": "linear-gradient(to right, #fff 67%, #ff0000 67%, #ff0000 78%, #ff8800 78%, #ff8800 89%, #808080 89%)"
    },
    "livery-1336": {
        "background": "linear-gradient(300deg, #0000 72%, #f39a1f 20%), linear-gradient(to top, #5768A0 20%, #F571BB 20%, #F571BB 27%, #A9B8E3 27%, #A9B8E3 47%, #E0EFFA 47%)"
    },
    "livery-1337": {
        "background": "linear-gradient(300deg, #0000 72%, #f7da30 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-1338": {
        "background": "linear-gradient(300deg, #0000 72%, #ea212d 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-1339": {
        "background": "linear-gradient(to top, #34709e 50%, #fed134 50%, #fed134 59%, #34709e 59%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1340": {
        "background": "#0034f0",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1341": {
        "background": "#b6343c",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1343": {
        "background": "linear-gradient(to top, #FFCA00 34%, #001B90 34%, #001B90 50%, #FFCA00 50%)",
        "stroke": "#FFCA00"
    },
    "livery-1344": {
        "background": "linear-gradient(to right, #ffffff 60%, transparent 60%), linear-gradient(120deg, #0000 67.5%, #fff 67.5%, #fff 77.5%, #0000 77.5%), linear-gradient(60deg, #005bb2 65%, #fff 65%, #fff 75%, #005bb2 75%)",
        "stroke": "#ffffff"
    },
    "livery-1345": {
        "background": "linear-gradient(120deg, #317b94 35%, #2eadff 35.1% 39%, #b0b7ba 39.1% 43%, #2d79f3 43.1% 47%, #317b94 47.1%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1346": {
        "background": "#e5459d",
        "color": "#ffffff",
        "fill": "#ffffff"
    },
    "livery-1348": {
        "background": "linear-gradient(to top, #0d3d94 20%, #fff 20%)"
    },
    "livery-1349": {
        "background": "linear-gradient(135deg, #FFDD00 50%, #FAB001 50%)"
    },
    "livery-1350": {
        "background": "radial-gradient(circle at left 45%, #3bc 35%, #077 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1355": {
        "background": "linear-gradient(to top, #2851c6 29%, #eb2e18 29%, #eb2e18 58%, #f5e42e 58%, #f5e42e 86%, #eb2e18 86%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1358": {
        "background": "linear-gradient(to top, #f5e9c2 22%, #11366c 22%, #11366c 29%, #f5e9c2 29%, #f5e9c2 50%, #11366c 50%, #11366c 58%, #f5e9c2 58%, #f5e9c2 72%, #11366c 72%, #11366c 79%, #f5e9c2 79%)",
        "color": "#11366c",
        "fill": "#11366c",
        "stroke": "#f5e9c2"
    },
    "livery-1359": {
        "background": "linear-gradient(to top, #895124 15%, #ec4332 15%, #ec4332 43%, #f4ddb5 43%)"
    },
    "livery-1362": {
        "background": "linear-gradient(to top, #f43b1d 50%, #f4e3a9 50%, #f4e3a9 59%, #f43b1d 59%, #f43b1d 75%, #f4e3a9 75%, #f4e3a9 84%, #f43b1d 84%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#f43b1d"
    },
    "livery-1363": {
        "background": "linear-gradient(to top, #1c49a2 46%, #f2ead3 46%, #f2ead3 55%, #1c49a2 55%, #1c49a2 64%, #f2ead3 64%, #f2ead3 73%, #1c49a2 73%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#1c49a2"
    },
    "livery-1365": {
        "background": "linear-gradient(to top, #133EAD 40%, #FFF1E0 40%, #FFF1E0 80%, #133EAD 80%)",
        "stroke": "#FFF1E0"
    },
    "livery-1366": {
        "background": "linear-gradient(300deg, #0000 72%, #f73f2d 20%), linear-gradient(to top, #5768A0 20%, #F571BB 20%, #F571BB 27%, #A9B8E3 27%, #A9B8E3 47%, #E0EFFA 47%)"
    },
    "livery-1367": {
        "background": "linear-gradient(to left, #6f3a96 20%, #f8b200 20%, #f8b200 45%, #6f3a96 45%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#6f3a96"
    },
    "livery-1368": {
        "background": "linear-gradient(to right, #400770 50%, #934193 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1369": {
        "background": "linear-gradient(270deg, #0000 95%, #F571BB 5%), linear-gradient(90deg, #0000 95%, #F571BB 5%), linear-gradient(to top, #5768A0 20%, #F571BB 20%, #F571BB 27%, #A9B8E3 27%, #A9B8E3 47%, #E0EFFA 47%)",
        "color": "#D7363E",
        "fill": "#D7363E"
    },
    "livery-1370": {
        "background": "linear-gradient(to top, #8ee600 40%, #feff36 40%)",
        "stroke": "#feff36"
    },
    "livery-1373": {
        "background": "linear-gradient(to top, #0f6db4 20%, transparent 20%), radial-gradient(circle at top left, transparent 60%, #40a1ff 60%, #40a1ff 70%, #085fad 70%), radial-gradient(circle at bottom center, #fff 84%, #40a1ff 84%, #40a1ff 92%, #085fad 92%)",
        "stroke": "#ffffff"
    },
    "livery-1374": {
        "background": "linear-gradient(to top, #ff0000 42%, transparent 42%, transparent 52%, #ff0000 52%), radial-gradient(circle at top left, #fde800 50%, #104fce 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1375": {
        "background": "linear-gradient(to top, #1C431A 25%, #52D143 25%, #52D143 38%, #1C431A 38%, #1C431A 50%, #F3E7AC 50%, #F3E7AC 63%, #F3E7A3 63%, #F3E7A3 75%, #F3E7AC 75%)"
    },
    "livery-1377": {
        "background": "linear-gradient(to top, #fff 20%, #837c83 20%, #837c83 30%, #ad2738 30%, #ad2738 40%, #fff 40%)"
    },
    "livery-1378": {
        "background": "#c2b593"
    },
    "livery-1380": {
        "background": "linear-gradient(to top, #7a7a7a 17%, #fff585 17%, #fff585 25%, #ff6f00 25%, #ff6f00 67%, #fff585 67%)"
    },
    "livery-1386": {
        "background": "linear-gradient(to top, #0f3281 20%, #fff 20%, #fff 25%, #e84190 25%, #e84190 40%, #fff 40%)",
        "stroke": "#ffffff"
    },
    "livery-1387": {
        "background": "linear-gradient(to top, #0f3281 20%, #fff 20%, #fff 25%, #f19203 25%, #f19203 40%, #fff 40%)",
        "stroke": "#ffffff"
    },
    "livery-1388": {
        "background": "linear-gradient(to top, #0f3281 20%, #ffffff 20%, #ffffff 25%, #76b81f 25%, #76b81f 40%, #ffffff 40%)",
        "stroke": "#ffffff"
    },
    "livery-1390": {
        "background": "linear-gradient(300deg, #0000 72%, #01a8ac 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-1392": {
        "background": "linear-gradient(300deg, #0000 72%, #811d6a 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-1393": {
        "background": "linear-gradient(300deg, #0000 72%, #811d6a 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-1394": {
        "background": "linear-gradient(300deg, #0000 28%, #ebf1fd 28%, #ebf1fd 31%, #0000 31%, #0000 39%, #ebf1fd 39%, #ebf1fd 66%, #f000 66%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), radial-gradient(circle at 5% 110%, #fff 25%, #af1b5b 25%, #af1b5b 30%, #04b2e2 30%, #04b2e2 35%, #009661 35%, #009661 40%, #f2cc35 40%, #f2cc35 45%, #f2821a 45%, #f2821a 50%, #e20000 50%, #e20000 55%, #fff 55%)",
        "stroke": "#ebf1fd"
    },
    "livery-1400": {
        "background": "linear-gradient(300deg, #0000 72%, #eae065 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-1401": {
        "background": "linear-gradient(to top, #FF6A00 40%, #FAD7B4 40%, #FAD7B4 60%, #6BAA2B 60%)"
    },
    "livery-1402": {
        "background": "linear-gradient(45deg, #057d45 25%, #057d45 25%, transparent 25%), linear-gradient(to top, #057d45 30%, #FFAD00 30%)"
    },
    "livery-1403": {
        "background": "linear-gradient(45deg, #101184 25%, #101184 25%, transparent 25%), linear-gradient(to top, #101184 30%, #FFAD00 30%)",
        "stroke": "#FFAD00"
    },
    "livery-1406": {
        "background": "linear-gradient(to top, #fff 65%, #9b0000 65%, #9b0000 85%, #fff 85%)"
    },
    "livery-1407": {
        "background": "linear-gradient(45deg, #fff 10%, #004a1c 10%, #004a1c 25%, transparent 25%), linear-gradient(to top, #004a1c 30%, #fff 30%)",
        "stroke": "#ffffff"
    },
    "livery-1408": {
        "background": "linear-gradient(45deg, #fff 10%, #004a1c 10%, #004a1c 25%, transparent 25%), linear-gradient(to top, #004a1c 30%, #fff 30%)",
        "stroke": "#ffffff"
    },
    "livery-1409": {
        "background": "linear-gradient(to right, #004faf 19%, #cecc35 19%, #cecc35 28%, #004faf 28%, #004faf 46%, #fff 46%, #fff 55%, #004faf 55%, #004faf 73%, #cecc35 73%, #cecc35 82%, #004faf 82%)",
        "stroke": "#FFFFFF"
    },
    "livery-1410": {
        "background": "linear-gradient(150deg, #008B92 50%, transparent 50%), linear-gradient(to top, #024450 40%, #008B92 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1411": {
        "stroke": "#ffbf00",
        "background": "linear-gradient(300deg, #0000 72%, #ffbf00 20%), linear-gradient(300deg, #004c1e 28%, #0000 28%), linear-gradient(#0000 85%, #ffbf00 85%), linear-gradient(300deg, #0000 31%, #3f8b4a 31% 39%, #0000 39%), #ffbf00"
    },
    "livery-1412": {
        "background": "linear-gradient(130deg, #FEDC00 35%, transparent 35.5%), linear-gradient(to top, #004C98 4%, transparent 4.5%), linear-gradient(250deg, transparent 0%, #004C98 0% 54%, transparent 54.5%), linear-gradient(147deg, transparent 52.5%, #004c98 53% 61%, transparent 61.5%), linear-gradient(139deg, transparent 45.5%, #2278cd 46% 52%, transparent 52.5%), linear-gradient(138deg, transparent 43.5%, #004c98 44% 47%, transparent 47.5%), linear-gradient(130deg, transparent 36.5%, #64b5f6 37% 43%, transparent 43.5%), #004C98",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#004C98"
    },
    "livery-1413": {
        "background": "linear-gradient(to top, #12073F 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #A7A5D2 60%, #A7A5D2 70%, #2F2554 70%)",
        "stroke": "#ffffff"
    },
    "livery-1415": {
        "background": "linear-gradient(to top, #472955 20%, transparent 20%), radial-gradient(circle at top left, transparent 60%, #e14ba2 60%, #e14ba2 70%, #472955 70%), radial-gradient(circle at bottom center, #fff 84%, #e14ba2 84%, #e14ba2 92%, #472955 92%)",
        "stroke": "#ffffff"
    },
    "livery-1419": {
        "background": "linear-gradient(to top, #122247 20%, #fff 20%, #fff 80%, #122247 80%)",
        "stroke": "#ffffff"
    },
    "livery-1420": {
        "background": "linear-gradient(300deg, #0000 72%, #ac7a3b 20%), linear-gradient(300deg, #2d3677 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #66aafd 31%, #66aafd 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-1426": {
        "background": "linear-gradient(52deg, #1364B1 0%, #3ABBFF 55%, #0A4D8C 100%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1429": {
        "background": "linear-gradient(300deg, #0000 72%, #ac7a3b 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-1430": {
        "background": "linear-gradient(to top, #8c0b05 20%, #b49862 20%, #b49862 30%, #fff 30%, #fff 60%, #8c0b05 60%, #8c0b05 80%, #fff 80%)",
        "stroke": "#ffffff"
    },
    "livery-1431": {
        "background": "radial-gradient(circle at 50% 155%, #fff 40%, transparent 60%), linear-gradient(to top, #74eeff, #3b75fc)"
    },
    "livery-1432": {
        "background": "#1a40d5",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1433": {
        "background": "linear-gradient(to top, #C71A26 43%, #F3F1E5 43%, #F3F1E5 47%, #2B3F8A 47%, #2B3F8A 58%, #F3F1E5 58%)",
        "stroke": "#F3F1E5"
    },
    "livery-1437": {
        "background": "#020350",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1440": {
        "background": "linear-gradient(to right, #34C624 34%, #FFF544 34%, #FFF544 45%, #34C624 45%)"
    },
    "livery-1441": {
        "background": "#c6ae7a"
    },
    "livery-1442": {
        "background": "radial-gradient(circle at 50% 48%, #dd6 0%, #ab30 40%), linear-gradient(to right, #683 40%, #0000 40%), radial-gradient(circle at 45% 50%, #683 50%, #ab3 53%)"
    },
    "livery-1443": {
        "background": "#79a3c1"
    },
    "livery-1444": {
        "background": "linear-gradient(to top, #a7a8ac 20%, #48b0cf 20%, #48b0cf 30%, #08070b 30%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1445": {
        "background": "linear-gradient(to top, #000 20%, #eaeaea 20%, #eaeaea 40%, #ffd500 40%)"
    },
    "livery-1449": {
        "background": "radial-gradient(circle at 50% 155%, #143A68 40%, transparent 60%), linear-gradient(to top, #3a2727, #FC834E)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1451": {
        "background": "#dd2833",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1454": {
        "background": "linear-gradient(to right, transparent 80%, #09493e 80%), linear-gradient(to top, #09493e 50%, #85d2f0 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-1455": {
        "background": "#14B728",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1456": {
        "background": "linear-gradient(to right, #8b0000 60%, #000 60%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1459": {
        "background": "#A3A3A3"
    },
    "livery-1461": {
        "background": "linear-gradient(to top, #880000 25%, #ffff88 25%, #ffff88 50%, #880000 50%, #880000 75%, #ffff88 75%)",
        "stroke": "#ffff88"
    },
    "livery-1465": {
        "background": "linear-gradient(295deg, #ff9712 19%, #FF8D02 19%, #FF8D02 28%, #86af01 28%, #86af01 37%, #0387e0 37%, #0387e0 46%, #0233b7 46%, #0233b7 55%, #d254d1 55%, #d254d1 64%, #ff3c2e 64%, #ff3c2e 73%, #ff9712 73%, #ff9712 82%, #FF8D02 82%, #FF8D02 91%, #86af01 91%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1468": {
        "background": "linear-gradient(300deg, #0000 72%, #0093f0 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-1469": {
        "background": "linear-gradient(120deg, #e30514 40%, #0e3cc4 40%, #0e3cc4 50%, #fff 50%)",
        "stroke": "#ffffff"
    },
    "livery-1471": {
        "background": "linear-gradient(to right, #a7b2b3 34%, #6a3994 34%, #6a3994 50%, #a083bb 50%, #a083bb 67%, #f7f7f7 67%, #f7f7f7 84%, #a7b2b3 84%)",
        "stroke": "#a7b2b3"
    },
    "livery-1473": {
        "background": "linear-gradient(to right, #95c1cd 10%, #fff 10%, #fff 50%, #129637 50%, #129637 60%, #78ba50 60%, #78ba50 70%, #fff 70%, #fff 90%, #0482ab 90%)",
        "stroke": "#FFFFFF"
    },
    "livery-1474": {
        "background": "linear-gradient(120deg, #e30514 40%, #0074cf 40%, #0074cf 50%, #fff 50%)",
        "stroke": "#ffffff"
    },
    "livery-1475": {
        "background": "linear-gradient(120deg, #e30514 40%, #232023 40%, #232023 50%, #ffffff 50%)",
        "stroke": "#ffffff"
    },
    "livery-1476": {
        "background": "linear-gradient(to top, #fff 17.5%, #920c19 17.5%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1477": {
        "background": "linear-gradient(to top, #1c2b64 17.5%, #920c19 17.5%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1479": {
        "background": "linear-gradient(110deg, #ED1B23 55%, #ffcf31 55%, #ffcf31 64%, #ffffff 64%, #ffffff 73%, #062591 73%)",
        "stroke": "#ffffff"
    },
    "livery-1480": {
        "background": "linear-gradient(to top, #fff 25%, #ed1d23 25%, #ed1d23 38%, #1f2879 38%, #1f2879 50%, #fff 50%)",
        "stroke": "#ffffff"
    },
    "livery-1482": {
        "background": "radial-gradient(circle at left 45%, #72cf5a 35%, #fc855a 45%)"
    },
    "livery-1483": {
        "background": "radial-gradient(circle at left 45%, #87BD25 35%, #262626 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1484": {
        "background": "radial-gradient(circle at left 45%, #65c658 35%, #fff 45%)"
    },
    "livery-1485": {
        "background": "radial-gradient(circle at left 45%, #88cc22 35%, #012e03 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1486": {
        "background": "radial-gradient(circle at left 45%, #87BD25 35%, #6a532c 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1487": {
        "background": "#000000",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1488": {
        "background": "linear-gradient(to right, #ff0000 17%, #6D8696 17%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1489": {
        "background": "linear-gradient(to right, #81e154 40%, #0042b5 40%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#0042b5"
    },
    "livery-1490": {
        "background": "linear-gradient(to top, #f1442b 19%, transparent 19%), radial-gradient(circle at top left, transparent 78%, #ffffff 78%, #ffffff 80%, #f1442b 80%), linear-gradient(to top, #f1442b 19%, #ffffff 19%, #ffffff 22%, #5fbdfe 22%, #5fbdfe 40%, transparent 40%), radial-gradient(circle at top left, #ffffff 66%, #5fbdfe 66%, #5fbdfe 78%, #ffffff 78%, #ffffff 80%, #f1442b 80%)"
    },
    "livery-1491": {
        "background": "linear-gradient(to top, #0d0e10 13%, #919ba9 13%, #919ba9 38%, #0d0e10 38%, #0d0e10 63%, #919ba9 63%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1494": {
        "background": "linear-gradient(to top, #56c1ff 17%, #2c6ac5 17%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1495": {
        "background": "linear-gradient(to top, #393a3e 27%, #fff 27%, #fff 34%, #f07527 34%, #f07527 40%, #fff 40%)"
    },
    "livery-1496": {
        "background": "radial-gradient(circle at left 45%, #3bc 35%, #077 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1497": {
        "background": "linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, transparent 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%), linear-gradient(to top, #0F6DB4 20%, #ffffff 20%, #ffffff 27%, #1c80ef 27%, #1c80ef 40%, transparent 40%), radial-gradient(circle at top left, #fff 52%, #1c80ef 52%, #1c80ef 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-1498": {
        "background": "linear-gradient(to right, #58348a 13%, #ffffff 13%, #ffffff 50%, #646e80 50%, #646e80 63%, #ffffff 63%, #ffffff 88%, #646e80 88%)",
        "stroke": "#ffffff"
    },
    "livery-1499": {
        "background": "linear-gradient(to right, #fb373e 10%, #ffffff 10%, #ffffff 46%, #fb373e 46%, #fb373e 64%, #ffffff 64%, #ffffff 91%, #fb373e 91%)",
        "stroke": "#ffffff"
    },
    "livery-1500": {
        "background": "radial-gradient(ellipse at 35% -45%, #a020f0 45%, transparent 45%), linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-1501": {
        "background": "#6F2C5F",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1502": {
        "background": "#efce59"
    },
    "livery-1503": {
        "background": "linear-gradient(to top, #dc241f 43%, #ef7c10 43%, #ef7c10 58%, #dc241f 58%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1504": {
        "background": "linear-gradient(to top, #132fb0 29%, #ffffff 29%, #ffffff 36%, #2193a4 36%, #2193a4 50%, #ffffff 50%)",
        "stroke": "#ffffff"
    },
    "livery-1505": {
        "background": "linear-gradient(to top, #0883e0 25%, #efe7ca 25%, #efe7ca 75%, #0883e0 75%)"
    },
    "livery-1506": {
        "background": "#39dbbd"
    },
    "livery-1507": {
        "background": "linear-gradient(to top, #282d2e 20%, #fff 20%, #fff 40%, #db171d 40%, #db171d 50%, #fff 50%, #fff 80%, #db171d 80%, #db171d 90%, #fff 90%)",
        "stroke": "#ffffff"
    },
    "livery-1508": {
        "background": "linear-gradient(to top, #b0d9d7 17%, #0370c9 17%, #0370c9 84%, #b0d9d7 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1510": {
        "background": "linear-gradient(300deg, #0000 72%, #f73f2d 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-1511": {
        "background": "linear-gradient(to top, #263967 25%, #ece5d3 25%)"
    },
    "livery-1513": {
        "background": "linear-gradient(110deg, #ff6700 55%, #fff 55%, #fff 62%, #2b2b8d 62%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#2B2B8D"
    },
    "livery-1514": {
        "background": "linear-gradient(to top, #e30106 22%, #fff 22%, #fff 37%, #8e1f30 37%, #8e1f30 43%, #fff 43%, #fff 48%, #8e1f30 48%, #8e1f30 53%, #fff 53%, #fff 69%, #e30106 69%)",
        "stroke": "#FFFFFF"
    },
    "livery-1518": {
        "background": "linear-gradient(to top, #0000 90%, #1175ce 90%), linear-gradient(130deg, #48c02e 35%, #fff 35% 55%, #48c02e 55%)"
    },
    "livery-1519": {
        "background": "linear-gradient(to right, #ffffff 56%, #343532 56%, #343532 67%, #be1219 67%)",
        "stroke": "#ffffff"
    },
    "livery-1520": {
        "background": "#76BB40"
    },
    "livery-1521": {
        "background": "linear-gradient(180deg, #0000 50%, #04b 50%), repeating-conic-gradient(from 18deg, #09d 12deg 24deg, #04b 24deg 36deg)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#0044bb"
    },
    "livery-1522": {
        "background": "radial-gradient(ellipse at bottom left, transparent 20%, #ffff00 20%, #ffff00 40%, transparent 40%), linear-gradient(to top, #b32531 20%, #ffff00 20%, #ffff00 80%, #b32531 80%)"
    },
    "livery-1523": {
        "background": "linear-gradient(180deg, #005BBB 50%, #FFD500 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#005bbb"
    },
    "livery-1525": {
        "background": "linear-gradient(100deg, #adadad 60%, #01aadb 60%, #01aadb 80%, #193276 80%)"
    },
    "livery-1526": {
        "background": "#f3343b",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1527": {
        "background": "linear-gradient(to top, #263967 25%, #ece5d3 25%, #ece5d3 75%, #0ea86f 75%)"
    },
    "livery-1528": {
        "background": "linear-gradient(to top, #ed1d23 25%, #1f2879 25%, #1f2879 50%, #fff 50%, #fff 88%, #fecb1b 88%)",
        "stroke": "#ffffff"
    },
    "livery-1530": {
        "background": "linear-gradient(to top, #c31e19 25%, #ffe7a7 25%, #ffe7a7 75%, #c31e19 75%)"
    },
    "livery-1531": {
        "background": "linear-gradient(100deg, #ffe7a7 56%, #84898a 56%, #84898a 78%, #c31e19 78%)"
    },
    "livery-1534": {
        "background": "linear-gradient(135deg, #c5d5df 10%, #50d1ff 10%, #50d1ff 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1537": {
        "background": "linear-gradient(to top, #327831 43%, #fff 43% 57%, #327831 57%)",
        "color": "#ffffff",
        "fill": "#ffffff",
        "stroke": "#599627"
    },
    "livery-1538": {
        "background": "linear-gradient(135deg, #c5d5df 10%, #c735a7 10%, #c735a7 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1539": {
        "background": "linear-gradient(135deg, #e67229 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1540": {
        "background": "linear-gradient(135deg, #ec4c86 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1541": {
        "background": "linear-gradient(135deg, #54c530 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1542": {
        "background": "linear-gradient(135deg, #6451bf 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1543": {
        "background": "linear-gradient(135deg, #81e33b 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1544": {
        "background": "linear-gradient(135deg, #2a83e0 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1545": {
        "background": "linear-gradient(135deg, #ffc507 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #9f1006 50%, #C50B0F 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1547": {
        "background": "linear-gradient(to top, #004B2A 34%, #c91818 34%, #c91818 67%, #7ED02D 67%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#004B2A"
    },
    "livery-1548": {
        "background": "linear-gradient(135deg, #ff0000 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1551": {
        "background": "linear-gradient(to top, #192c47 16%, #0d308d 16%, #0d308d 20%, #718699 20%, #718699 24%, #0d308d 24%, #0d308d 70%, #192c47 70%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1552": {
        "background": "linear-gradient(to right, #fff 15%, #624997 15%, #624997 72%, #1a3460 72%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1554": {
        "background": "linear-gradient(135deg, #21a3b9 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1555": {
        "background": "linear-gradient(135deg, #1c64ff 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #9f1006 50%, #C50B0F 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1556": {
        "background": "linear-gradient(135deg, #ff0000 10%, #999EA2 10%, #999EA2 15%, #ff0000 15%, #ff0000 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1557": {
        "background": "linear-gradient(135deg, #d83668 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1558": {
        "background": "linear-gradient(135deg, #37cc79 20%, #ff0000 20%, #ff0000 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1559": {
        "background": "linear-gradient(135deg, #a0b32d 6.25%, #71b527 6.25%, #71b527 12.5%, #3fab38 12.5%, #3fab38 18.75%, #109a45 18.75%, #109a45 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1561": {
        "background": "linear-gradient(135deg, #68AD49 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #9f1006 50%, #C50B0F 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1562": {
        "background": "linear-gradient(150deg, #0066db 40%, transparent 40%), linear-gradient(120deg, #ffffff 70%, #0dd0fc 70%)",
        "stroke": "#ffffff"
    },
    "livery-1563": {
        "background": "linear-gradient(135deg, #8134a5 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #9f1006 50%, #C50B0F 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1564": {
        "background": "linear-gradient(115deg, #fff 58%, #ba1111 58%, #ba1111 72%, #084ab4 72%)"
    },
    "livery-1566": {
        "background": "linear-gradient(60deg, #fff 20%, #e21822 20%, #e21822 35%, #1e44b1 35%, #1e44b1 50%, transparent 50%), linear-gradient(180deg, #fff 70%, #1e44b1 70%)",
        "stroke": "#ffffff"
    },
    "livery-1567": {
        "background": "#ed1c24",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1569": {
        "background": "linear-gradient(135deg, #303234 20%, #999EA2 20%, #999EA2 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1572": {
        "background": "linear-gradient(135deg, #8f8f8f 25%, transparent 25%, transparent 75%), linear-gradient(to top, #9f1006 50%, #C50B0F 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1573": {
        "background": "linear-gradient(135deg, #ff0000 5%, #2a83e0 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #3D3D3D 50%, #53575A 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1574": {
        "background": "#F25A43",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1576": {
        "background": "radial-gradient(at 62% 60%, #0bd 25%, #0000 25%), radial-gradient(at 77% 52%, #8c2 30%, #0000 30%), radial-gradient(at 47% 22%, #07b 63%, #0000 63%), linear-gradient(5deg, #0000 63%, #07b 63%), #8c2",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#0077bb"
    },
    "livery-1577": {
        "background": "#f7d921",
        "color": "#000000",
        "fill": "#000000"
    },
    "livery-1578": {
        "background": "#f57c0b",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-1579": {
        "background": "radial-gradient(circle at -20% 25%, #25B0CF 48%, #ff3c00 48%, #ff3c00 56%, #FFFF 56%, #FFFF 62%, #25B0CF 62%)"
    },
    "livery-1583": {
        "background": "#ee1d23",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1584": {
        "background": "#153e73",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1585": {
        "background": "linear-gradient(to top, #FFFD38 20%, transparent 20%, transparent 40%, #FFFD38 40%), linear-gradient(135deg, #bd0000 70%, #FFFD38 70%)",
        "stroke": "#FFFD38"
    },
    "livery-1586": {
        "background": "linear-gradient(to top, #156a1f 40%, #7fc71b 40%, #7fc71b 60%, #156a1f 60%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1587": {
        "background": "linear-gradient(to top, #559c43 40%, #fff 40%, #fff 60%, #559c43 60%)"
    },
    "livery-1588": {
        "background": "linear-gradient(to top, #db241e 50%, #fff 50%, #fff 84%, #db241e 84%)"
    },
    "livery-1589": {
        "background": "#ee1d23",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1590": {
        "background": "linear-gradient(60deg, #3d0e16 35%, #fba61b 36%, #fba61b 39%, #fff 40%, #fff 43%, #a5191a 46%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1591": {
        "background": "linear-gradient(60deg, #ee1d23 35%, #f6ac10 36%, #f6ac10 38%, #fff 39%, #fff 41%, #e30715 42%, #e30715 44%, #f7e74a 45%, #f7e74a 47%, #ee1d23 48%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1592": {
        "background": "linear-gradient(60deg, #73ba5e 35%, #000 36%, #000 38%, #92e778 39%, #92e778 41%, #fff 42%, #fff 44%, #0071bc 45%, #0071bc 47%, #73ba5e 48%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#254494"
    },
    "livery-1594": {
        "background": "linear-gradient(to top, #9F0F06 42%, #C50B0F 42%, #C50B0F 84%, #fddb14 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1595": {
        "background": "linear-gradient(to top, #9F0F06 42%, #C50B0F 42%, #C50B0F 84%, #343643 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1597": {
        "background": "linear-gradient(to top, #9F0F06 42%, #C50B0F 42%, #C50B0F 84%, #fdcf42 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1599": {
        "background": "linear-gradient(to top, #9F0F06 42%, #C50B0F 42%, #C50B0F 84%, #fc8042 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1602": {
        "background": "linear-gradient(to top, #9F0F06 42%, #C50B0F 42%, #C50B0F 84%, #fd4b81 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1603": {
        "background": "linear-gradient(135deg, #fff 25%, transparent 25%), linear-gradient(to top, #2B2B8D 25%, #FF6700 25%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1606": {
        "background": "linear-gradient(135deg, #fff 25%, transparent 25%), linear-gradient(to top, #2B2B8D 25%, #FF6700 25%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1610": {
        "background": "linear-gradient(to top, #EA2639 20%, transparent 20%), radial-gradient(circle at top left, transparent 60%, #F79F48 60%, #F79F48 70%, #0f6db4 70%), radial-gradient(circle at bottom center, #EA2639 84%, #0f6db4 84%, #0f6db4 92%, #0f6db4 92%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1612": {
        "background": "linear-gradient(14deg, #255 20%, #0000 20%), linear-gradient(to left, #487 30%, transparent 30%), radial-gradient(circle at 80% 50%, #487 40%, #8cc 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1614": {
        "background": "linear-gradient(to left, #504c49 50%, transparent 50%), radial-gradient(circle at center, #504c49 58%, #ffffff 58%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1615": {
        "background": "radial-gradient(circle at 54% 46%, #504C49 49%, #fff0 49%), radial-gradient(circle at 50% 50%, #fff 56%, #fff0 56%), linear-gradient(270deg, #504C49 50%, #bba 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1617": {
        "background": "linear-gradient(to right, #686763 10%, #00a1d8 10%)"
    },
    "livery-1620": {
        "background": "linear-gradient(to top, #2d2d2c 15%, #0000 15%), linear-gradient(125deg, #2d2d2c 30%, #a8c542 30%, #a8c542 50%, #2d2d2c 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1621": {
        "background": "linear-gradient(to top, #fff 35%, #a8c542 35%, #a8c542 40%, #fff 40%)"
    },
    "livery-1629": {
        "background": "linear-gradient(to top, #6e2447 38%, #f06d97 38%, #f06d97 50%, #6e2447 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1630": {
        "background": "#fef2cf"
    },
    "livery-1631": {
        "background": "linear-gradient(to top, #3b89fe 25%, #fff 25%)"
    },
    "livery-1632": {
        "background": "linear-gradient(to top, transparent 83%, #41a0f8 83%), linear-gradient(to right, #E73323 34%, #A52A23 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1633": {
        "background": "linear-gradient(to top, transparent 83%, #fb7d44 83%), linear-gradient(to right, #E73323 34%, #A52A23 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1634": {
        "background": "linear-gradient(to top, transparent 83%, #2fcad1 83%), linear-gradient(to right, #E73323 34%, #A52A23 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1635": {
        "background": "radial-gradient(130% 145% at 10% 25%, #0480 60%, #ccc 60%), radial-gradient(circle at 100% 140%, #048 92%, #ccc 92%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1636": {
        "background": "linear-gradient(to left, #bd58c8 15%, #12287e 15%, #12287e 22%, #bd58c8 22%, #bd58c8 36%, #12287e 36%, #12287e 43%, #bd58c8 43%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1637": {
        "background": "radial-gradient(circle at top left, #ec98c000 70%, #4a2f42 70%), radial-gradient(circle at -5% -20%, #d590 65%, #d59 65%), radial-gradient(circle at bottom center, #ec98c0 84%, #d59 84%, #d59 92%, #4a2f42 92%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1639": {
        "background": "radial-gradient(at bottom, #f90 40%, #0000 40%), repeating-conic-gradient(from 11deg at bottom, #0a4 0deg 9deg, #094 9deg 12deg, #073 12deg 27deg, #094 27deg 30deg)"
    },
    "livery-1643": {
        "background": "radial-gradient(at bottom, #f80 40%, #0000 40%), repeating-conic-gradient(from 11deg at bottom, #e31 0deg 9deg, #c12 9deg 12deg, #911 12deg 27deg, #c12 27deg 30deg)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#ff8800"
    },
    "livery-1644": {
        "background": "radial-gradient(at bottom, #6cf 40%, #0000 40%), repeating-conic-gradient(from 11deg at bottom, #3be 0deg 9deg, #17b 9deg 12deg, #15a 12deg 27deg, #17b 27deg 30deg)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1647": {
        "background": "repeating-conic-gradient(from 90deg at 80% 100%, #046 0deg 50deg, #f45 50deg 68deg, #079 68deg 75deg, #046 75deg 100deg, #3cc 100deg 120deg, #046 120deg 180deg)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#004466"
    },
    "livery-1648": {
        "background": "repeating-conic-gradient(from 90deg at 80% 100%, #046 0deg 50deg, #cd3 50deg 68deg, #079 68deg 75deg, #046 75deg 100deg, #3cc 100deg 120deg, #046 120deg 180deg)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#004466"
    },
    "livery-1649": {
        "background": "repeating-conic-gradient(from 90deg at 80% 100%, #046 0deg 50deg, #f72 50deg 68deg, #079 68deg 75deg, #046 75deg 100deg, #3cc 100deg 120deg, #046 120deg 180deg)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#004466"
    },
    "livery-1650": {
        "background": "repeating-conic-gradient(from 90deg at 80% 100%, #046 0deg 50deg, #3ca 50deg 68deg, #079 68deg 75deg, #046 75deg 100deg, #3cc 100deg 120deg, #046 120deg 180deg)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#004466"
    },
    "livery-1651": {
        "background": "linear-gradient(300deg, #0000 72%, #ffbf00 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ffbf00 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #ffbf00",
        "stroke": "#ffbf00"
    },
    "livery-1652": {
        "background": "linear-gradient(to top, #2B5D64 20%, transparent 20%), radial-gradient(at top left, #F0F0C8 35%, transparent 35%), linear-gradient(to top, #FFD800 20%, #FFD800 24%, transparent 0%), radial-gradient(circle at 0 20%, #29BFCF 35%, #29BFCF 40%)"
    },
    "livery-1656": {
        "background": "linear-gradient(to top, #041283 50%, #edb03f 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1657": {
        "background": "linear-gradient(to top, #2224AD 50%, #E9F1FD 50%)",
        "stroke": "#E9F1FD"
    },
    "livery-1658": {
        "background": "linear-gradient(to top, #2224AD 38%, #E9F1FD 38%, #E9F1FD 63%, #2224AD 63%, #2224AD 75%, #E9F1FD 75%)",
        "stroke": "#E9F1FD"
    },
    "livery-1660": {
        "background": "linear-gradient(to top, #f2b610 25%, #FFFFFF 25%)"
    },
    "livery-1662": {
        "background": "radial-gradient(circle at 8% 50%, #f92 35%, #0bb 35%, #066 63%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#00665f"
    },
    "livery-1664": {
        "background": "#AB217F",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1669": {
        "background": "linear-gradient(110deg, #d6d6d6 55%, #595959 55%, #595959 64%, #ffffff 64%, #ffffff 73%, #552f7d 73%)",
        "stroke": "#d6d6d6"
    },
    "livery-1671": {
        "background": "linear-gradient(to top, #4d931b 34%, #e5cc91 34%, #e5cc91 67%, #4d931b 67%)"
    },
    "livery-1706": {
        "background": "linear-gradient(135deg, #cdaa84 25%, transparent 25%, transparent 75%), linear-gradient(0deg, #9f1006 50%, #C50B0F 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1707": {
        "background": "linear-gradient(to top, #9F0F06 42%, #C50B0F 42%, #C50B0F 84%, #cdaa84 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1709": {
        "background": "linear-gradient(0deg, #3d3d3d 15%, #c50b0f00 15%), radial-gradient(at top left, #bc1315 45%, transparent 45%), linear-gradient(90deg, #fff 65%, transparent 65%), radial-gradient(at top center, #fff 65%, #bc1315 65%)",
        "stroke": "#ffffff"
    },
    "livery-1710": {
        "background": "linear-gradient(to top, #007ec7 50%, #abd8dc 50%)"
    },
    "livery-1711": {
        "background": "linear-gradient(to top, #fff 5%, #e24640 5%, #e24640 9%, #fff 9%, #fff 13%, #707277 13%, #707277 17%, #fff 17%, #fff 21%, #3a352f 21%, #3a352f 25%, #fff 25%)"
    },
    "livery-1712": {
        "background": "linear-gradient(to top, #9fdb67 50%, #fff 50%)"
    },
    "livery-1713": {
        "background": "linear-gradient(to top, #c0151a 50%, #fff 50%)"
    },
    "livery-1714": {
        "background": "linear-gradient(to top, #2493c7 13%, #fde151 13%, #fde151 50%, #d32e2c 50%, #d32e2c 63%, #fde151 63%)"
    },
    "livery-1716": {
        "background": "linear-gradient(300deg, #0000 72%, #30444d 20%), linear-gradient(to top, #5768A0 20%, #F571BB 20%, #F571BB 27%, #A9B8E3 27%, #A9B8E3 47%, #E0EFFA 47%)"
    },
    "livery-1718": {
        "background": "linear-gradient(55deg, #0000 0%, #0000 30%, #e863ac 30%, #e863ac 33%, #0000 33%, #0000 35%, #e863ac 35%, #e863ac 38%, #0000 38%, #0000 41%, #e863ac 41%, #e863ac 44%, #0000 44%, #0000 47%, #e863ac 47%, #e863ac 50%, #0000 50%, #0000 53%, #e863ac 53%, #e863ac 56%, #0000 56%, #0000 59%, #e863ac 59%, #e863ac 62%, transparent 10%), linear-gradient(90deg, #fff 0%, #fff 95%, transparent 10%), linear-gradient(to bottom, #0000 0%, #0000 60%, #66caec 60%, #66caec 65%, #0000 65%, #0000 70%, #66caec 70%, #66caec 75%, #0000 75%, #0000 80%, #66caec 80%, #66caec 85%, #0000 85%, #0000 90%, #66caec 90%, #66caec 95%, transparent 10%)"
    },
    "livery-1720": {
        "background": "linear-gradient(75deg, #0B80D7 34%, #153D8A 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1726": {
        "background": "linear-gradient(to top, #0AA2C1 15%, #0084D5 15%, #0084D5 29%, #004D89 29%)",
        "color": "#ffffff",
        "fill": "#ffffff"
    },
    "livery-1727": {
        "background": "linear-gradient(120deg, #f39a1f 35%, transparent 35%), linear-gradient(to top, #5768A0 20%, #F571BB 20%, #F571BB 27%, #A9B8E3 27%, #A9B8E3 47%, #E0EFFA 47%)"
    },
    "livery-1728": {
        "background": "linear-gradient(120deg, #bbceed 35%, transparent 35%), linear-gradient(to top, #5768A0 20%, #F571BB 20%, #F571BB 27%, #A9B8E3 27%, #A9B8E3 47%, #E0EFFA 47%)"
    },
    "livery-1731": {
        "background": "linear-gradient(#aed9ff 40%, #40aaf0 40%, #40aaf0 60%, #5cbcfb 60%, #5cbcfb 80%, #f4bf9a 80%, #f4bf9a 100%)"
    },
    "livery-1732": {
        "background": "linear-gradient(360deg, #e1392e 0%, #881c43 10%, #40297e 20%, #17318a 30%, #2161b1 40%, #198bb3 50%, #126b73 60%, #399f49 70%, #9db53b 80%, #bb7643 90%, #93333a 100%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1735": {
        "background": "linear-gradient(to right, #FFFF00 10%, #9cad61 10%)"
    },
    "livery-1736": {
        "background": "linear-gradient(to bottom, #000 50%, transparent 50%, transparent 80%, #f3331c 80%), linear-gradient(60deg, #f3331c 25%, #000 25%, #000 50%, transparent 50%), linear-gradient(120deg, transparent 50%, #000 50%, #000 75%, #f3331c 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1737": {
        "background": "linear-gradient(to top, #2f7185 20%, transparent 20%), radial-gradient(circle at top left, #9ee03b 70%, #2f7185 70%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1739": {
        "background": "linear-gradient(300deg, #0000 72%, #f73f2d 20%), linear-gradient(to top, #5768A0 20%, #F571BB 20%, #F571BB 27%, #A9B8E3 27%, #A9B8E3 47%, #E0EFFA 47%)"
    },
    "livery-1744": {
        "background": "#024086",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1745": {
        "background": "linear-gradient(to right, #ffffff 20%, #024086 20%, #024086 24%, #00B5F1 24%, #00B5F1 27%, #024086 27%, #024086 30%, #00B5F1 30%, #00B5F1 34%, #024086 34%, #024086 37%, #00B5F1 37%, #00B5F1 40%, #024086 40%, #024086 44%, #ffffff 44%)",
        "stroke": "#ffffff"
    },
    "livery-1746": {
        "background": "radial-gradient(circle at 72% 35%, #62CBCC 42%, transparent 42%), radial-gradient(circle at 50% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 98% 5%, #62CBCC 15%, transparent 15%), radial-gradient(circle at 80% 30%, #008080 45%, #C9DAEA 45%)"
    },
    "livery-1747": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #41B752 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #008080 45%, #41B752 45%)"
    },
    "livery-1748": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #e34292 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #edc0d6 45%, #e34292 45%)"
    },
    "livery-1749": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #008EE2 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #013e61 45%, #008EE2 45%)"
    },
    "livery-1750": {
        "background": "radial-gradient(circle at 50% 45%, #C9DAEA 60%, #008EE2 40%)"
    },
    "livery-1751": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #003C72 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #518dc4 45%, #003C72 45%)",
        "stroke": "#C9DAEA"
    },
    "livery-1752": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #FFE000 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #de9a2c 45%, #FFE000 45%)"
    },
    "livery-1753": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #7BBAF9 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #013e61 45%, #7BBAF9 45%)"
    },
    "livery-1754": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #F64332 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #821c12 45%, #F64332 45%)"
    },
    "livery-1755": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #BBAAE0 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #462196 45%, #BBAAE0 45%)"
    },
    "livery-1756": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #BBAAE0 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #462196 45%, #BBAAE0 45%)"
    },
    "livery-1757": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #F0890C 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #b04f0e 45%, #F0890C 45%)"
    },
    "livery-1758": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #4F3117 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #875b35 45%, #4F3117 45%)",
        "stroke": "#C9DAEA"
    },
    "livery-1759": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #62CBCC 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #a3eff0 45%, #62CBCC 45%)"
    },
    "livery-1760": {
        "background": "radial-gradient(circle at 50% 45%, #C9DAEA 60%, #62CBCC 40%)"
    },
    "livery-1761": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #481473 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #BBAAE0 45%, #481473 45%)",
        "stroke": "#C9DAEA"
    },
    "livery-1762": {
        "background": "radial-gradient(circle at 72% 35%, #C9DAEA 42%, transparent 42%), radial-gradient(circle at 50% 5%, #9AF41F 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #2e8555 45%, #9AF41F 45%)"
    },
    "livery-1763": {
        "background": "radial-gradient(circle at 72% 35%, #c9daea 42%, transparent 42%), radial-gradient(circle at 50% 5%, #fff 15%, transparent 15%), radial-gradient(circle at 98% 5%, #c9daea 15%, transparent 15%), radial-gradient(circle at 80% 30%, #9e2b20 45%, #fff 45%)"
    },
    "livery-1764": {
        "background": "radial-gradient(circle at 72% 35%, #62CBCC 42%, transparent 42%), radial-gradient(circle at 50% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 98% 5%, #62CBCC 15%, transparent 15%), radial-gradient(circle at 80% 30%, #008080 45%, #C9DAEA 45%)"
    },
    "livery-1765": {
        "background": "linear-gradient(45deg, #df4f84 24%, #ffffff 24%, #ffffff 31%, #df4f84 31%, #df4f84 47%, #ffffff 47%, #ffffff 54%, #df4f84 54%, #df4f84 85%, #ffffff 85%, #ffffff 93%, #df4f84 93%)",
        "stroke": "#ffffff"
    },
    "livery-1766": {
        "background": "linear-gradient(45deg, #df4f84 24%, #fff 24%, #fff 31%, #46a2cc 31%, #46a2cc 47%, #fff 47%, #fff 54%, #46a2cc 54%, #46a2cc 85%, #fff 85%, #fff 93%, #df4f84 93%)"
    },
    "livery-1767": {
        "background": "linear-gradient(45deg, #df4f84 24%, #fff 24%, #fff 31%, #73aa15 31%, #73aa15 47%, #fff 47%, #fff 54%, #73aa15 54%, #73aa15 85%, #fff 85%, #fff 93%, #df4f84 93%)"
    },
    "livery-1768": {
        "background": "#78d9f6"
    },
    "livery-1769": {
        "background": "#0c9ef6",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1770": {
        "background": "linear-gradient(to right, #14c2fd 10%, #ff0000 10%, #ff0000 15%, #f67511 15%, #f67511 20%, #ffff00 20%, #ffff00 25%, #34782d 25%, #34782d 30%, #2734a4 30%, #2734a4 35%, #602b63 35%, #602b63 40%, #e071ac 40%, #e071ac 45%, #1ba4ae 45%, #1ba4ae 50%, #6c4027 50%, #6c4027 55%, #000000 55%, #000000 60%, #04977b 60%, #04977b 70%, #14c2fd 70%, #14c2fd 80%, #ffffff 80%, #ffffff 90%, #faae00 90%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1771": {
        "background": "linear-gradient(to bottom, #FDC52E 70%, transparent 70%), linear-gradient(120deg, #c00000 40%, #FDC52E 40%, #FDC52E 45%, #2d6ec6 45%, #2d6ec6 65%, #c00000 65%)",
        "stroke": "#FDC52E"
    },
    "livery-1772": {
        "background": "linear-gradient(to bottom, #1d1d1e 10%, #fdc931 10%, #fdc931 70%, transparent 70%), linear-gradient(120deg, #eb222d 40%, #fdc931 40%, #fdc931 45%, #1d1d1e 45%, #1d1d1e 65%, #eb222d 65%)",
        "stroke": "#FDC52E"
    },
    "livery-1773": {
        "background": "linear-gradient(to bottom, #000 10%, #fdc52e 10%, #fdc52e 70%, transparent 70%), linear-gradient(120deg, #fdc52e 45%, #c00000 45%)",
        "stroke": "#FDC52E"
    },
    "livery-1780": {
        "background": "linear-gradient(to right, #00B5F1 30%, #ef6b1f 30%, #ef6b1f 50%, #0042B5 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1781": {
        "background": "linear-gradient(to right, #00B5F1 30%, #fc3a41 30%, #fc3a41 50%, #0042B5 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1782": {
        "background": "linear-gradient(to right, #00B5F1 30%, #eb3ea7 30%, #eb3ea7 50%, #0042B5 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1783": {
        "background": "linear-gradient(to right, #00B5F1 30%, #33ee66 30%, #33ee66 50%, #0042B5 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1785": {
        "background": "linear-gradient(to top, transparent 83%, #ce3e4e 83%), linear-gradient(to right, #35baff 80%, #2853ef 80%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1786": {
        "background": "linear-gradient(to bottom, #FDC52E 10%, #FDC52E 70%, transparent 70%), linear-gradient(120deg, #FDC52E 45%, #c00000 45%)",
        "stroke": "#FDC52E"
    },
    "livery-1789": {
        "background": "linear-gradient(135deg, #A8B3B5 34%, #404040 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1790": {
        "background": "linear-gradient(135deg, #A8B3B5 32%, #404040 32%, #404040 69%, #42915D 69%, #42915D 75%, #B0404C 75%, #B0404C 82%, #2B5899 82%, #2B5899 88%, #42915D 88%, #42915D 94%, #B0404C 94%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1792": {
        "stroke": "#f8d232",
        "background": "linear-gradient(285deg, #f8d232 43%, #000 43% 58%, #fff 58% 72%, #f8d232 72%)"
    },
    "livery-1794": {
        "background": "linear-gradient(to top, #fff 29%, #ff829e 29%, #ff829e 43%, #fff 43%, #fff 72%, #ff829e 72%)"
    },
    "livery-1795": {
        "background": "linear-gradient(to top, #38328c 29%, #5cbd64 29%, #5cbd64 72%, #d49d3f 72%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1797": {
        "background": "radial-gradient(at bottom right, #b4b9bb 70%, #e93a3f 70%)"
    },
    "livery-1798": {
        "background": "radial-gradient(at top right, #193143 65%, #bd0000 65%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1799": {
        "background": "linear-gradient(to top, #3e6eac 20%, transparent 20%), radial-gradient(circle at top left, #a1acb6 65%, #3e6eac 65%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1800": {
        "background": "linear-gradient(to top, #ed1d23 25%, #1f2879 25%, #1f2879 50%, #fff 50%, #fff 88%, #41b6c1 88%)",
        "stroke": "#ffffff"
    },
    "livery-1801": {
        "background": "linear-gradient(to top, #0d96df 25%, #113065 25%, #113065 50%, #fff 50%, #fff 75%, #0d96df 75%)",
        "stroke": "#ffffff"
    },
    "livery-1802": {
        "background": "linear-gradient(to top, #233b7f 20%, #ffd745 20%, #ffd745 30%, #2e80ec 30%, #2e80ec 90%, #ffd745 90%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1803": {
        "background": "linear-gradient(to top, #f8393f 23%, #000000 23%, #000000 34%, #ffffff 34%)",
        "stroke": "#ffffff"
    },
    "livery-1808": {
        "background": "linear-gradient(0deg, #09302d 8%, #d4d1b8 8%, #d4d1b8 12%, #1c6017 12%, #1c6017 50%, #d4d1b8 50%, #d4d1b8 54%, #1c6017 54%, #1c6017 68%, #d4d1b8 68%, #d4d1b8 72%, #1c6017 72%, #1c6017 92%, #d4d1b8 0%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1809": {
        "background": "radial-gradient(circle at 4% 50%, #ce4088 16%, #0000 0%), radial-gradient(circle at 96% 50%, #ce4088 16%, #0000 0%), linear-gradient(to left, #752c63 16%, #0000 0% 84%, #752c63 0%), conic-gradient(from 220deg at 25.3% 50%, #ce4088 0deg 100deg, #0000 0deg 360deg), conic-gradient(from 40deg at 74.7% 50%, #ce4088 0deg 100deg, #0000 0deg 360deg), radial-gradient(circle at -17% 0%, #752c63 40%, #0000 20%), radial-gradient(circle at 117% 0%, #752c63 40%, #0000 20%), radial-gradient(circle at -17% 100%, #752c63 40%, #0000 20%), radial-gradient(circle at 117% 100%, #752c63 40%, #0000 20%), #f57cb2",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#752c63"
    },
    "livery-1810": {
        "background": "conic-gradient(from 315deg at 23% 25%, #f22 0deg 90deg, #0000 90deg), conic-gradient(from 315deg at 43% 35%, #f22 0deg 90deg, #0000 90deg), conic-gradient(from 135deg at 44% 65%, #f22 0deg 90deg, #0000 90deg), conic-gradient(from 135deg at 64% 75%, #f22 0deg 90deg, #0000 90deg), linear-gradient(45deg, #f22 36%, #fff 36%, #fff 40%, #f22 40%, #f22 44%, #fff 44%, #fff 48%, #f22 48%, #f22 52%, #fff 52%, #fff 56%, #f22 56%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#ff2222"
    },
    "livery-1811": {
        "background": "linear-gradient(120deg, #fd5c02 67%, #2e3855 67%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1812": {
        "background": "radial-gradient(ellipse at 35% -45%, #1e8da8 45%, transparent 45%), linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-1813": {
        "background": "radial-gradient(ellipse at 35% -45%, #909ea4 45%, transparent 45%), linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-1814": {
        "background": "linear-gradient(to top, #e03716 43%, #fff 43%, #fff 57%, #e03716 57%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-1815": {
        "background": "#C2C2C2"
    },
    "livery-1817": {
        "background": "linear-gradient(to top, #ef7f1a 15%, #fff 15% 90%, #ef7f1a 80%)"
    },
    "livery-1828": {
        "background": "#cbffcb"
    },
    "livery-1834": {
        "background": "linear-gradient(140deg, #74A921 60%, transparent 60%), linear-gradient(150deg, #8DBA18 70%, #ABC519 75%)"
    },
    "livery-1835": {
        "stroke": "#ebf1fd",
        "background": "linear-gradient(300deg, #0000 72%, #0093f0 20%), linear-gradient(300deg, #004c1e 28%, #0000 28%), linear-gradient(#0000 85%, #ebf1fd 85%), linear-gradient(300deg, #0000 31%, #3f8b4a 31% 39%, #0000 39%), #ebf1fd"
    },
    "livery-1836": {
        "background": "linear-gradient(to right, #bc9876 15%, #fff 15%, #fff 25%, #bc9876 25%, #bc9876 45%, #fff 45%, #fff 55%, #bc9876 55%, #bc9876 75%, #fff 75%, #fff 85%, #bc9876 85%)",
        "stroke": "#ffffff"
    },
    "livery-1837": {
        "background": "linear-gradient(to top, #6251B1 34%, #EC5C96 34%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#EC5C96"
    },
    "livery-1839": {
        "background": "linear-gradient(45deg, #ECE9D3 10%, #FE7E0A 10%, #FE7E0A 25%, transparent 25%), linear-gradient(to top, #FE7E0A 30%, #ECE9D3 30%)"
    },
    "livery-1844": {
        "background": "radial-gradient(at top left, #fcde3f 60%, #2ec0f9 60%, #2ec0f9 65%, #1558c1 65%)"
    },
    "livery-1850": {
        "background": "repeating-conic-gradient(from 227deg at 78% 97%, #0000 0deg 90deg, #fff 90deg 95deg, #fff0 95deg 97deg, #fff 97deg 102deg, #0000 102deg 360deg), linear-gradient(235deg, #f18602 45%, #c02156 45%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#f18602"
    },
    "livery-1884": {
        "background": "linear-gradient(65deg, transparent 80%, #24448f 80%), linear-gradient(120deg, transparent 49%, #f9f7fb 49%, #f9f7fb 77.5%, #24448f 77.5%), linear-gradient(65deg, #24448f 50%, #f9f7fb 50%, #f9f7fb 77%, #24448f 77%)",
        "stroke": "#ffffff"
    },
    "livery-1886": {
        "background": "radial-gradient(at top left, transparent 75%, #192053 75%), linear-gradient(180deg, transparent 70%, #1a90c6 70%, #1a90c6 78%, #192053 78%), linear-gradient(125deg, #fddd01 60%, #1a90c6 60%)"
    },
    "livery-1889": {
        "background": "radial-gradient(circle at left 45%, #88cc22 35%, #009f9a 45%)"
    },
    "livery-1896": {
        "background": "linear-gradient(to right, #FDEC80 43%, #ECC178 43%, #ECC178 58%, #AD9044 58%, #AD9044 72%, #13A7CB 72%, #13A7CB 86%, #A30A2F 86%)"
    },
    "livery-1900": {
        "background": "linear-gradient(110deg, #95c962 55%, #e6bd0d 55%, #e6bd0d 64%, #fff 64%, #fff 73%, #7ece28 73%)"
    },
    "livery-1901": {
        "background": "radial-gradient(circle at 36% 400%, #e0d8ca 80%, #211351 65%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-1907": {
        "background": "linear-gradient(120deg, #fe362f 40%, #d3d8de 40%, #d3d8de 50%, transparent 50%), linear-gradient(to bottom, #d3d8de 70%, #999e9b 70%)"
    },
    "livery-1911": {
        "background": "linear-gradient(to top, #8c0b05 15%, #c24d4a 15%, #c24d4a 20%, transparent 20%), linear-gradient(135deg, #fff 50%, transparent 50%, transparent 55%, #fff 55%, #fff 60%, transparent 60%, transparent 65%, #fff 65%, #fff 70%, transparent 70%, transparent 75%, #fff 75%, #fff 80%, transparent 80%, transparent 85%, #fff 85%), linear-gradient(45deg, #fff 65%, #c24d4a 65%, #c24d4a 70%, #fff 70%, #fff 75%, #b49862 75%, #b49862 80%, #fff 80%, #fff 85%, #c24d4a 85%, #c24d4a 90%, #fff 90%, #fff 95%, #b49862 95%, #b49862 100%, #fff 100%)"
    },
    "livery-1912": {
        "background": "linear-gradient(to top, #1f8f5f 40%, #614ab3 40%, #614ab3 50%, #9ba4ab 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1914": {
        "background": "#f6eac8"
    },
    "livery-1918": {
        "background": "#949494"
    },
    "livery-1920": {
        "background": "#f6eac7"
    },
    "livery-1925": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #54A441 95%), linear-gradient(to top, #fff 48%, #54A441 48%, #54A441 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1926": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #DF154D 95%), linear-gradient(to top, #fff 48%, #DF154D 48%, #DF154D 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1927": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #A388E5 95%), linear-gradient(to top, #fff 48%, #A388E5 48%, #A388E5 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1928": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #46AA50 95%), linear-gradient(to top, #fff 48%, #46AA50 48%, #46AA50 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1929": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #C86E32 95%), linear-gradient(to top, #fff 48%, #C86E32 48%, #C86E32 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1930": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #F0D228 95%), linear-gradient(to top, #fff 48%, #F0D228 48%, #F0D228 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1931": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #37AF96 95%), linear-gradient(to top, #fff 48%, #37AF96 48%, #37AF96 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1932": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #E63C5A 95%), linear-gradient(to top, #fff 48%, #E63C5A 48%, #E63C5A 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1933": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #D7AA87 95%), linear-gradient(to top, #fff 48%, #D7AA87 48%, #D7AA87 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1934": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #5ABEBE 95%), linear-gradient(to top, #fff 48%, #5ABEBE 48%, #5ABEBE 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1935": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #966EAF 95%), linear-gradient(to top, #fff 48%, #966EAF 48%, #966EAF 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1936": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #87A7AB 95%), linear-gradient(to top, #fff 48%, #87A7AB 48%, #87A7AB 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1937": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #E15FA0 95%), linear-gradient(to top, #fff 48%, #E15FA0 48%, #E15FA0 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1938": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #D75032 95%), linear-gradient(to top, #fff 48%, #D75032 48%, #D75032 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1939": {
        "background": "linear-gradient(45deg, #fff 10%, #8B0E04 10%, #8B0E04 25%, transparent 25%), linear-gradient(to top, #8B0E04 30%, transparent 30%), linear-gradient(90deg, #0000 95%, #5FC35F 95%), linear-gradient(to top, #fff 48%, #5FC35F 48%, #5FC35F 63%, #fff 63%)",
        "stroke": "#ffffff"
    },
    "livery-1940": {
        "background": "linear-gradient(to top, transparent 55%, #0088ff 55%), radial-gradient(at 99% 120%, #ff8800 55%, #0088ff 55%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1942": {
        "background": "linear-gradient(to top, #597318 30%, #fff5de 30%, #fff5de 50%, #bd5734 50%, #bd5734 80%, #fff5de 80%)",
        "stroke": "#fff5de"
    },
    "livery-1946": {
        "background": "linear-gradient(60deg, #EC5C96 35%, transparent 35%), linear-gradient(90deg, transparent 30%, #312B6B 120%), linear-gradient(0deg, #312B6B 10%, #5E5D85 10%, #5E5D85 14%, #312B6B 14%, #312B6B 18%, #5E5D85 18%, #5E5D85 22%, #312B6B 22%, #312B6B 26%, #5E5D85 26%, #5E5D85 30%, #312B6B 30%, #312B6B 34%, #5E5D85 34%, #5E5D85 39%, #312B6B 39%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#312B6B"
    },
    "livery-1947": {
        "background": "linear-gradient(135deg, #312B6B 35%, #EC5C96 35%, #EC5C96 52%, #312B6B 52%)"
    },
    "livery-1948": {
        "background": "linear-gradient(180deg, transparent 80%, #939998 80%), radial-gradient(at 117% 264%, #939998 57.5%, #e75740 57.5%, #e75740 60%, #e6f6f3 60%, #e6f6f3 62.5%, #2d5ca1 62.5%, #2d5ca1 65%, #939998 65%)"
    },
    "livery-1949": {
        "background": "linear-gradient(to top, #000000 25%, #fdc52e 25%)",
        "stroke": "#FFFFFF"
    },
    "livery-1950": {
        "background": "linear-gradient(to top, #000000 25%, #fdc52e 25%)",
        "stroke": "#FFFFFF"
    },
    "livery-1951": {
        "background": "linear-gradient(to top, #000000 25%, #fdc52e 25%)",
        "stroke": "#FFFFFF"
    },
    "livery-1952": {
        "background": "linear-gradient(180deg, transparent 80%, #2a92d0 80%), radial-gradient(circle at top left, transparent 75%, #5e6b6e 75%, #5e6b6e 80%, #2a92d0 80%), linear-gradient(180deg, #fff 70%, #5e6b6e 70%)"
    },
    "livery-1966": {
        "background": "#99c4bd"
    },
    "livery-1972": {
        "background": "#0088ff",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1973": {
        "background": "#3d464d",
        "color": "#ffffff",
        "fill": "#ffffff"
    },
    "livery-1982": {
        "background": "linear-gradient(180deg, #79889f 60%, transparent 60%), linear-gradient(120deg, #79889f 40%, #3d4b5d 40%)",
        "color": "#ffffff",
        "fill": "#ffffff"
    },
    "livery-1983": {
        "background": "linear-gradient(151deg, transparent 65%, #1c2e42 65%), linear-gradient(155deg, #fff 60%, #1d99e5 60%)",
        "stroke": "#ffffff"
    },
    "livery-1984": {
        "background": "linear-gradient(180deg, #f7ce61 20%, #307663 20%, #307663 75%, #f7ce61 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-1989": {
        "background": "#304079",
        "color": "#ffffff",
        "fill": "#ffffff"
    },
    "livery-1998": {
        "background": "linear-gradient(120deg, #3463bd 35%, #39b7ea 35%, #3c6bc3 55%)",
        "color": "#ffffff",
        "fill": "#ffffff"
    },
    "livery-2001": {
        "background": "radial-gradient(at bottom right, #dfc26d 35%, #fc7522 35%)"
    },
    "livery-2002": {
        "background": "radial-gradient(at bottom right, #1755c2 35%, #fff 35%)",
        "stroke": "#ffffff"
    },
    "livery-2003": {
        "background": "linear-gradient(to top, #4aaaf0 13%, #f0e7c6 13%, #f0e7c6 38%, #4aaaf0 38%, #4aaaf0 63%, #f0e7c6 63%, #f0e7c6 88%, #4aaaf0 88%)"
    },
    "livery-2004": {
        "background": "linear-gradient(to top, #31a17e 50%, #21262e 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2008": {
        "background": "linear-gradient(180deg, #FF0000 70%, #ddc38c 70%, #ddc38c 80%, #FF0000 80%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2012": {
        "background": "linear-gradient(to top, #335d43 20%, transparent 20%), linear-gradient(to right, #ffd600 50%, transparent 50%), radial-gradient(circle at -10% 50%, #ffd600 80%, #da4f2e 80%, #da4f2e 85%, #335d43 85%)"
    },
    "livery-2015": {
        "background": "radial-gradient(circle at 86% 50%, #486AB0 35%, #80C651 35%)"
    },
    "livery-2016": {
        "background": "#18332E",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2029": {
        "background": "linear-gradient(226deg, #2e1f75 60%, #0000 72%), radial-gradient(ellipse at 23% 145%, #5b4ca1 39%, #2e1f75 10%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2030": {
        "background": "#3085da",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2037": {
        "background": "#666666",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2038": {
        "background": "linear-gradient(to top, #fff 50%, #b31e55 50%)",
        "color": "#ffffff",
        "fill": "#ffffff",
        "stroke": "#000000"
    },
    "livery-2044": {
        "background": "linear-gradient(to right, #34C624 34%, #0f4ff2 34%, #0f4ff2 45%, #34C624 45%)",
        "stroke": "#34C624"
    },
    "livery-2048": {
        "background": "linear-gradient(to top, #EE1959 34%, #f0d375 34%)"
    },
    "livery-2055": {
        "background": "radial-gradient(circle at -20% 25%, #9602a1 48%, #919191 48%, #919191 56%, #FFFF 56%, #FFFF 62%, #25B0CF 62%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2060": {
        "background": "#00c4ff"
    },
    "livery-2066": {
        "background": "linear-gradient(180deg, #da0101 80%, #313539 80%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2068": {
        "background": "#FF8000"
    },
    "livery-2070": {
        "background": "linear-gradient(130deg, #0088ff 12%, #fff 12%, #fff 24%, #0088ff 24%, #0088ff 36%, #fff 36%, #fff 48%, #0088ff 48%, #0088ff 60%, #fff 60%, #fff 72%, #0088ff 72%, #0088ff 84%, #fff 84%, #fff 96%, #0088ff 96%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2071": {
        "background": "radial-gradient(circle at top left, #ff0000 60%, #ff8800 60%, #ff8800 70%, #0088ff 70%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2072": {
        "background": "linear-gradient(to right, #F5DF68 25%, #FFFFFF 25%, #FFFFFF 50%, #F5DF68 50%, #F5DF68 75%, #066CFA 75%)"
    },
    "livery-2073": {
        "background": "#1f3f7b",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2075": {
        "background": "#90f886"
    },
    "livery-2076": {
        "background": "radial-gradient(circle at 72% 35%, #673AA6 42%, transparent 42%), radial-gradient(circle at 50% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 98% 5%, #673AA6 15%, transparent 15%), radial-gradient(circle at 80% 30%, #ffffff 45%, #C9DAEA 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2077": {
        "background": "linear-gradient(65deg, #3D90FB 35%, transparent 35%), linear-gradient(180deg, #3D90FB 10%, #FFFF00 10%, #ffff00 18%, #3D90FB 18%, #3D90FB 20%, #FFFF00 20%, #FFFF00 28%, #3D90FB 28%)",
        "stroke": "#FFFFFF"
    },
    "livery-2081": {
        "background": "linear-gradient(to right, #b03841 5%, transparent 5%, transparent 85%, #b03841 85%), radial-gradient(circle at 90% 80%, #b03841 50%, #f16a8b 50%, #f16a8b 65%, #e0d5b5 65%, #e0d5b5 86%, #b03841 86%)",
        "color": "#ffffff",
        "fill": "#ffffff"
    },
    "livery-2082": {
        "background": "#441196",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2083": {
        "background": "#A3191F",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2117": {
        "background": "linear-gradient(to top, #069C7B 20%, #ACB2A8 20%, #ACB2A8 50%, #069C7B 50%, #069C7B 70%, #ACB2A8 70%)",
        "stroke": "#ACB2A8"
    },
    "livery-2118": {
        "background": "linear-gradient(to top, #8c0b05 40%, #b49862 40%, #b49862 50%, #fff 50%)",
        "stroke": "#ffffff"
    },
    "livery-2121": {
        "background": "linear-gradient(180deg, #dc241f 25%, transparent 25%, transparent 75%, #dc241f 75%), linear-gradient(90deg, #f59e72 20%, #dc241f 20%, #dc241f 40%, #b04058 40%, #b04058 60%, #eeb46c 60%, #eeb46c 80%, #dc241f 80%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2122": {
        "background": "linear-gradient(to top, #ffffff 20%, #2e2c6c 20%, #2e2c6c 80%, #ffffff 80%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2125": {
        "background": "linear-gradient(to top, #8c0b05 20%, #fff 20%, #fff 50%, #8c0b05 50%, #8c0b05 70%, #fff 70%)",
        "stroke": "#ffffff"
    },
    "livery-2126": {
        "background": "linear-gradient(180deg, #072b4d 10%, #f7e6cc 10%, #f7e6cc 25%, #072b4d 25%, #072b4d 45%, #f7e6cc 45%, #f7e6cc 65%, #072b4d 65%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2127": {
        "background": "linear-gradient(90deg, #eb8921 45%, transparent 45%, transparent 55%, #0066bb 55%), linear-gradient(180deg, #ca0310 85%, #0066bb 85%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2128": {
        "background": "linear-gradient(180deg, #fff 80%, #ea5f86 80%)"
    },
    "livery-2129": {
        "background": "#0080d4",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2130": {
        "background": "linear-gradient(90deg, #fff 25%, #f45314 25%, #f45314 38%, #d21415 38%, #d21415 50%, #fff 50%)",
        "stroke": "#ffffff"
    },
    "livery-2131": {
        "background": "#70cb77"
    },
    "livery-2132": {
        "background": "#fdb7fe"
    },
    "livery-2133": {
        "background": "#006d55",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2134": {
        "background": "linear-gradient(to top, #142b8b 10%, #ffffff 10%, #ffffff 15%, #6cbae0 15%, #6cbae0 24%, #ffffff 24%, #ffffff 29%, #c6292a 29%, #c6292a 34%, #ffffff 34%)"
    },
    "livery-2135": {
        "background": "linear-gradient(90deg, #07c4ff 10%, #fff 10%, #fff 50%, transparent 50%, transparent 70%, #fff 70%, #fff 90%, transparent 90%), linear-gradient(180deg, #ff0000 20%, #ffa500 20%, #ffa500 40%, #00ff00 40%, #00ff00 60%, #0000ff 60%, #0000ff 80%, #a020f0.80%)",
        "stroke": "#ffffff"
    },
    "livery-2136": {
        "background": "linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #52cac1 70%, #52cac1 85%, #EA2639 85%)"
    },
    "livery-2137": {
        "background": "linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #005c14 70%, #005c14 85%, #EA2639 85%)"
    },
    "livery-2138": {
        "background": "#96d35f"
    },
    "livery-2139": {
        "background": "linear-gradient(180deg, #CC3333 38%, #eef0e1 38%, #eef0e1 50%, #CC3333 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#CC3333"
    },
    "livery-2140": {
        "background": "linear-gradient(90deg, #dfc18e 10%, transparent 10%, transparent 50%, #037 50%), radial-gradient(ellipse 96% 118% at 60% 50%, transparent 50%, #6bf 50%), radial-gradient(circle at 57% 50%, #037 55%, #ff5 55%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2142": {
        "background": "linear-gradient(to right, #98b719 50%, #00baeb 50%, #00baeb 67%, #1F3D0C 67%, #1F3D0C 84%, #3f872b 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2143": {
        "background": "radial-gradient(ellipse at 35% -45%, #1c80ef 45%, transparent 45%), linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-2144": {
        "background": "linear-gradient(120deg, #c42180 29%, #b8c4d2 29%, #b8c4d2 72%, #6738ac 72%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2145": {
        "background": "radial-gradient(circle at 50% 45%, #66AB38 60%, #bbaae0 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2148": {
        "background": "linear-gradient(to right, #483baf 40%, #ffffff 40%)",
        "stroke": "#ffffff"
    },
    "livery-2149": {
        "background": "#0e78d8",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2150": {
        "background": "linear-gradient(120deg, #fff 55%, #0000 55%), linear-gradient(180deg, #fff 5%, #0000 5%, #0000 15%, #fff 15%, #fff 25%, #0000 25%, #0000 35%, #fff 35%, #fff 45%, #0000 45%, #0000 55%, #fff 55%, #fff 65%, #0000 65%, #0000 75%, #fff 75%, #fff 85%, #0000 85%, #0000 95%, #fff 95%), linear-gradient(90deg, #fff 30%, #006f4f 30%, #006f4f 37.5%, #fff 37.5%, #fff 40%, #0d9e3a 40%, #0d9e3a 47.5%, #fff 47.5%, #fff 50%, #59bd50 50%, #59bd50 57.5%, #fff 57.5%, #fff 60%, #006f4f 60%, #006f4f 67.5%, #fff 67.5%, #fff 70%, #0d9e3a 70%, #0d9e3a 77.5%, #fff 77.5%, #fff 80%, #59bd50 80%, #59bd50 87.5%, #fff 87.5%, #fff 90%, #006f4f 90%, #006f4f 97.5%, #fff 97.5%)",
        "stroke": "#ffffff"
    },
    "livery-2151": {
        "background": "radial-gradient(ellipse at 35% -10%, #ffffff 16%, #0AB5E0 16%, #0AB5E0 17%, #0078B4 17%, #0078B4 18%, #04538B 18%, #04538B 19%, #103F6B 19%, #103F6B 20%, transparent 20%), radial-gradient(ellipse at 35% -45%, #103F6B 39%, #04538B 39%, #04538B 41%, #0078B4 41%, #0078B4 43%, #0AB5E0 43%, #0AB5E0 45%, transparent 45%), linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#ffffff"
    },
    "livery-2152": {
        "background": "linear-gradient(to top, #ffff00 34%, #000 34%, #000 67%, #ffff00 67%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2153": {
        "background": "radial-gradient(circle at 50% 107%, #AF1B5B 5%, #AF1B5B 10%, #04B2E2 10%, #04B2E2 15%, #009661 15%, #009661 20%, #F2CC35 20%, #F2CC35 25%, #F2821A 25%, #F2821A 30%, #E20000 30%, #E20000 35%, transparent 35%), linear-gradient(135deg, #C70C10 40%, #771613 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2154": {
        "background": "radial-gradient(circle at 50% 107%, #AF1B5B 5%, #AF1B5B 10%, #04B2E2 10%, #04B2E2 15%, #009661 15%, #009661 20%, #F2CC35 20%, #F2CC35 25%, #F2821A 25%, #F2821A 30%, #E20000 30%, #E20000 35%, transparent 35%), linear-gradient(135deg, #1DA0DB 34%, #0055A4 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2157": {
        "background": "linear-gradient(120deg, #646571 35%, #32bcee 35%, #32bcee 45%, #4d5a6d 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2161": {
        "background": "linear-gradient(120deg, #646571 35%, #C50B0F 35%, #C50B0F 45%, #4d5a6d 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2168": {
        "background": "linear-gradient(to right, #07c4ff 10%, #fff 10%, #fff 50%, #f6df26 50%, #f6df26 60%, #3c3823 60%, #3c3823 70%, #fff 70%, #fff 90%, #f6df26 90%)",
        "stroke": "#ffffff"
    },
    "livery-2169": {
        "background": "linear-gradient(to top, #00bb00 17%, #ffffff 17%, #ffffff 67%, #00bb00 67%)",
        "stroke": "#ffffff"
    },
    "livery-2170": {
        "background": "linear-gradient(75deg, #000 20%, transparent 20%), linear-gradient(105deg, #00bb00 80%, #000 80%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2171": {
        "background": "linear-gradient(180deg, #fff 55%, #ffff00 55%, #ffff00 70%, #ffa500 70%, #ffa500 85%, #ff0000 85%)"
    },
    "livery-2176": {
        "background": "linear-gradient(85deg, #fff 67%, #0000 67%), linear-gradient(170deg, #25228c 47%, #00FF00 47%, #00FF00 52%, #ADD8E6 52%, #ADD8E6 57%, #FF0000 57%, #FF0000 62%, #FFFF00 62%, #FFFF00 67%, #25228c 67%)"
    },
    "livery-2210": {
        "background": "linear-gradient(180deg, #e69d04 70%, #2480af 70%, #2480af 80%, #6a83a0 80%, #6a83a0 90%, #e69d04 90%)"
    },
    "livery-2216": {
        "background": "#7b7f86",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2217": {
        "background": "linear-gradient(300deg, #8b001d 28%, #0000 28%), linear-gradient(to top, #ed1d23 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #f7941e 31%, #f7941e 39%, #0000 39%), #ed1d23",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2218": {
        "background": "linear-gradient(300deg, #8b001d 28%, #0000 28%), linear-gradient(to top, #ed1d23 15%, #0000 15%), linear-gradient(300deg, #ed1d23 31%, #f7941e 31%, #f7941e 39%, #ed1d23 39%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2219": {
        "background": "#464649",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2220": {
        "background": "radial-gradient(at bottom right, #c0c0c0 30%, #000 30%, #000 35%, #fff 35%)",
        "stroke": "#ffffff"
    },
    "livery-2223": {
        "background": "#326BA8",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2227": {
        "background": "linear-gradient(to right, #985d96 50%, #ab81e5 50%, #ab81e5 75%, #5f40b2 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2229": {
        "background": "linear-gradient(to right, #afbdc8 50%, #ab81e5 50%, #ab81e5 75%, #5f40b2 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2231": {
        "background": "linear-gradient(to right, #fe4b4f 50%, #ab81e5 50%, #ab81e5 75%, #5f40b2 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2232": {
        "background": "linear-gradient(to right, #da5e94 50%, #ab81e5 50%, #ab81e5 75%, #5f40b2 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2234": {
        "background": "linear-gradient(to right, #297fca 50%, #ab81e5 50%, #ab81e5 75%, #5f40b2 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2235": {
        "background": "linear-gradient(to right, #6ce4da 50%, #ab81e5 50%, #ab81e5 75%, #5f40b2 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2236": {
        "background": "linear-gradient(to right, #c0ea7a 50%, #ab81e5 50%, #ab81e5 75%, #5f40b2 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2237": {
        "background": "linear-gradient(to right, #01bf61 50%, #ab81e5 50%, #ab81e5 75%, #5f40b2 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2238": {
        "background": "linear-gradient(90deg, #67b73c 10%, #105CA9 10%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2239": {
        "background": "linear-gradient(to top, #ffff00 50%, #fff 50%)"
    },
    "livery-2241": {
        "background": "#00ff00",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2243": {
        "background": "linear-gradient(to right, #767267 12%, #f26e2d 12%, #f26e2d 23%, #767267 23%, #767267 34%, #f26e2d 34%, #f26e2d 45%, #767267 45%, #767267 56%, #f26e2d 56%, #f26e2d 78%, #767267 78%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2244": {
        "background": "linear-gradient(to right, #5d1650 50%, #a53055 50%, #a53055 75%, #d0386a 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2245": {
        "background": "#08ffd2"
    },
    "livery-2246": {
        "background": "#FF6F00"
    },
    "livery-2249": {
        "background": "linear-gradient(110deg, #fff 40%, #ed1b23 50%, #ed1b23 55%, #ffcf31 55%, #ffcf31 64%, #fff 64%, #fff 73%, #005da3 73%)",
        "color": "#000000",
        "fill": "#000000",
        "stroke": "#FFFFFF"
    },
    "livery-2250": {
        "background": "linear-gradient(to top, #B00E00 40%, #F8F0C6 40%, #F8F0C6 60%, #B00E00 60%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#B00E00"
    },
    "livery-2251": {
        "background": "#99c4bd"
    },
    "livery-2253": {
        "background": "linear-gradient(180deg, #121116 5%, #87CEEB 5%, #87CEEB 20%, #121116 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2254": {
        "background": "linear-gradient(180deg, #121116 5%, #b47ede 5%, #b47ede 20%, #121116 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2255": {
        "background": "linear-gradient(180deg, #121116 5%, #24793d 5%, #24793d 20%, #121116 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2257": {
        "background": "#feffa8"
    },
    "livery-2258": {
        "background": "linear-gradient(to top, #0f6db4 20%, transparent 20%), radial-gradient(at top left, #fff 62%, #ffa500 62%, #ffa500 67%, #fff 67%, #fff 70%, #0f6db4 70%)"
    },
    "livery-2259": {
        "background": "#800000",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2260": {
        "background": "radial-gradient(circle at left, #fff 35%, #5dd454 35%, #5dd454 40%, #264a6b 40%, #264a6b 65%, #5cbb77 75%)",
        "stroke": "#ffffff"
    },
    "livery-2262": {
        "background": "#adadad"
    },
    "livery-2263": {
        "background": "linear-gradient(180deg, #417082 50%, #cfcfcd 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2264": {
        "background": "linear-gradient(180deg, #307838 38%, #b9dc9d 38%, #b9dc9d 50%, #307838 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#307838"
    },
    "livery-2265": {
        "background": "radial-gradient(at top, #0000 75%, #516667 75%), linear-gradient(180deg, #50a7f6 40%, #fff 70%, #73b353 70%)"
    },
    "livery-2267": {
        "background": "radial-gradient(circle at top left, #20b359 40%, #fff 40%, #fff 43%, #2b7d4c 43%)",
        "stroke": "#ffffff"
    },
    "livery-2270": {
        "background": "linear-gradient(90deg, #0000 30%, #fff 30%, #fff 40%, #ff0000 40%, #ff0000 60%, #fff 60%, #fff 70%, #0000 70%), linear-gradient(45deg, #00008b 10%, #fff 10%, #fff 20%, #ff0000 20%, #ff0000 38%, #0000 38%), linear-gradient(135deg, #0000 62%, #ff0000 62%, #ff0000 80%, #0000 80%, #0000 90%, #00008b 90%), linear-gradient(45deg, #fff 43%, #0000 43%), linear-gradient(135deg, #00008b 57%, #fff 57%)",
        "stroke": "#ffffff"
    },
    "livery-2271": {
        "background": "linear-gradient(90deg, #0000 30%, #fff 30%, #fff 40%, #ff0000 40%, #ff0000 60%, #fff 60%, #fff 70%, #0000 70%), linear-gradient(45deg, #00008b 10%, #fff 10%, #fff 20%, #ff0000 20%, #ff0000 38%, #0000 38%), linear-gradient(135deg, #0000 62%, #ff0000 62%, #ff0000 80%, #0000 80%, #0000 90%, #00008b 90%), linear-gradient(45deg, #fff 43%, #0000 43%), linear-gradient(135deg, #00008b 57%, #fff 57%)",
        "stroke": "#ffffff"
    },
    "livery-2272": {
        "background": "linear-gradient(180deg, #510400 20%, #fff 20%, #fff 25%, #510400 25%, #510400 35%, #fff 35%, #fff 40%, #510400 40%, #510400 70%, #fff 70%, #fff 75%, #510400 75%)",
        "stroke": "#FFFFFF"
    },
    "livery-2273": {
        "background": "linear-gradient(180deg, #fff 25%, #3ba56d 25%, #3ba56d 50%, #fff 50%)"
    },
    "livery-2277": {
        "background": "#41a9e0",
        "stroke": "#FFFFFF"
    },
    "livery-2278": {
        "background": "linear-gradient(60deg, #73ba5e 35%, #61871f 35.1% 38%, #0071bc 38.1% 41%, #fff 41.1% 44%, #92e778 44.1% 47%, #005794 47.1%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2279": {
        "background": "linear-gradient(to top, #964B00 34%, #FFFDD0 34%, #FFFDD0 67%, #964B00 67%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2281": {
        "background": "#464649",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2283": {
        "background": "#fff700"
    },
    "livery-2284": {
        "background": "linear-gradient(300deg, #0000 72%, #e41e26 20%), linear-gradient(300deg, #6f0f16 28%, #0000 28%), linear-gradient(to top, #e41e26 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #ffea03 31%, #ffea03 39%, #0000 39%), #e41e26",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2285": {
        "background": "linear-gradient(170deg, #0000 81%, #6232a0 81%), linear-gradient(160deg, #0000 69%, #0c88e7 69%), linear-gradient(150deg, #0000 60%, #02ae36 60%), linear-gradient(140deg, #0000 53%, #f6d21d 53%), linear-gradient(130deg, #0000 46%, #e3422e 46%), linear-gradient(120deg, #EC5C96 40%, #e11132 40%)",
        "color": "#ffffff",
        "fill": "#ffffff"
    },
    "livery-2288": {
        "background": "linear-gradient(120deg, #e30514 35%, #43a6c9 35%, #43a6c9 42.6%, #0074cf 42.5%, #0074cf 50%, #fff 50%)",
        "stroke": "#ffffff"
    },
    "livery-2323": {
        "background": "#c28756"
    },
    "livery-2324": {
        "background": "linear-gradient(300deg, #BD0000 40%, #FFFD38 40%, #FFFD38 45%, #BD0000 45%, #BD0000 50%, #0000 50%), linear-gradient(180deg, #FFFD38 70%, #BD0000 70%, #BD0000 80%, #FFFD38 80%)"
    },
    "livery-2326": {
        "background": "#5c6271",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2327": {
        "background": "#BF9B30"
    },
    "livery-2328": {
        "background": "linear-gradient(125deg, #9ee03b 50%, #ffffff 50%)"
    },
    "livery-2329": {
        "background": "linear-gradient(180deg, #196F3D 50%, #FEF5E7 50%, #FEF5E7 84%, #196F3D 84%)",
        "stroke": "#FFFFFF"
    },
    "livery-2331": {
        "background": "linear-gradient(180deg, #0e2566 25%, #FFFDD0 25%, #FFFDD0 45%, #0e2566 45%, #0e2566 55%, #FFFDD0 55%, #FFFDD0 80%, #0e2566 80%)",
        "stroke": "#FFFFFF"
    },
    "livery-2366": {
        "background": "linear-gradient(to top, #437d4a 10%, #f9eece 10%, #f9eece 45%, #437d4a 45%, #437d4a 60%, #f9eece 60%)",
        "stroke": "#f9eece"
    },
    "livery-2367": {
        "background": "linear-gradient(305deg, #800080 15%, #0000FF 15%, #0000FF 29%, #ADD8E6 29%, #ADD8E6 43%, #228B22 43%, #228B22 58%, #90ee90 58%, #90ee90 72%, #FFFF00 72%, #FFFF00 86%, #ff0000 86%)",
        "stroke": "#FFFFFF"
    },
    "livery-2368": {
        "background": "linear-gradient(120deg, #04b139 40%, #d3d8de 40%, #d3d8de 50%, transparent 50%), linear-gradient(to bottom, #d3d8de 70%, #999e9b 70%)"
    },
    "livery-2401": {
        "background": "linear-gradient(300deg, #6f0910 28%, #0000 28%), linear-gradient(to top, #ecd28c 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9599c 31%, #a9599c 39%, #0000 39%), linear-gradient(to top, #ecd28c 60%, #0000 60%), linear-gradient(300deg, #0000 80%, #ce1e21 20%), #ecd28c",
        "stroke": "#ffffff"
    },
    "livery-2405": {
        "background": "linear-gradient(to top, #c6cbc5 50%, #88919a 50%)"
    },
    "livery-2408": {
        "background": "linear-gradient(to top, #0F6DB4 20%, #0000 20%), radial-gradient(circle at bottom right, #0000 90%, #0F6DB4 90%), radial-gradient(circle at top left, #0000 70%, #F79F48 70%, #F79F48 80%, #EA2639 80%), linear-gradient(180deg, #ffffff 30%, #0000 30%, #0000 50%, #ffffff 50%), linear-gradient(115deg, #0000 55%, #9b5a8a 55%), linear-gradient(75deg, #d9bb65 30%, #d5917c 30%)",
        "stroke": "#ffffff"
    },
    "livery-2409": {
        "background": "linear-gradient(to top, #0F6DB4 20%, #0000 20%), radial-gradient(circle at top left, #0000 70%, #F79F48 70% 80%, #EA2639 80%), radial-gradient(circle at bottom right, #ffffff 90%, #FFA500 90% 95%, #0F6DB4 95%)",
        "stroke": "#ffffff"
    },
    "livery-2410": {
        "background": "linear-gradient(125deg, #61a953 35%, #0000 35%), linear-gradient(180deg, #61a953 65%, #153665 65%, #153665 70%, #a2b2b5 70%, #a2b2b5 70%, #a2b2b5 75%, #153665 75%, #153665 80%, #a2b2b5 80%, #a2b2b5 85%, #153665 85%, #153665 90%, #a2b2b5 90%, #a2b2b5 95%, #153665 95%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2412": {
        "background": "linear-gradient(to right, #FFFF00 10%, #433459 10%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2413": {
        "background": "radial-gradient(circle at 92% 53%, #fff 7%, #0000 7.5%), radial-gradient(circle at 87% 57%, #fff 7%, #0000 7.5%), radial-gradient(circle at 90% 57%, #fff 6%, #bebfc3 6.5%, #bebfc3 7.5%, #0000 8%), radial-gradient(circle at 101% 117%, #006cb9 25%, #0000 25.5%), radial-gradient(circle at 90% 140%, #006cb9 35%, #0000 35.5%), linear-gradient(-40deg, #006cb9 16%, #bebfc3 16.5%, #bebfc3 18.5%, #0000 19%), radial-gradient(circle at 90% 140%, #006cb9 35%, #bebfc3 35.5%, #bebfc3 37.5%, #0000 38%), linear-gradient(0deg, #fff 0%, #fff 100%)"
    },
    "livery-2424": {
        "background": "repeating-conic-gradient(from 227deg at 78% 97%, #0000 0deg 90deg, #fff 90deg 95deg, #fff0 95deg 97deg, #fff 97deg 102deg, #0000 102deg 360deg), linear-gradient(235deg, #f18602 45%, #0091ea 45%)",
        "stroke": "#ffffff"
    },
    "livery-2425": {
        "background": "linear-gradient(300deg, #4d30a2 28%, #0000 28%, #0000 72%, #d5137e 20%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #EBF1FD 31%, #d56d20 31%, #d56d20 39%, #EBF1FD 39%)"
    },
    "livery-2426": {
        "background": "linear-gradient(to right, #ffffff 7%, #ff0000 7%, #ff0000 13%, #f67511 13%, #f67511 18%, #ffff00 18%, #ffff00 22%, #34782d 22%, #34782d 26%, #2734a4 26%, #2734a4 30%, #602b63 30%, #602b63 34%, #e071ac 34%, #e071ac 38%, #1ba4ae 38%, #1ba4ae 42%, #6c4027 42%, #6c4027 46%, #000000 46%, #000000 50%, #b1a98d 50%, #b1a98d 67%, #ffffff 67%, #ffffff 84%, #b1a98d 84%)",
        "stroke": "#ffffff"
    },
    "livery-2427": {
        "background": "linear-gradient(to right, #00B5F1 40%, #ffffff 40%)"
    },
    "livery-2428": {
        "background": "linear-gradient(105deg, #4c5259 40%, #51beff 40%)",
        "stroke": "#ffffff"
    },
    "livery-2433": {
        "background": "#e23f37",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2434": {
        "background": "linear-gradient(to right, #2271b6 6%, #6bafd6 6%, #6bafd6 11%, #4292c7 11%, #4292c7 16%, #2373b7 16%, #2373b7 22%, #09519d 22%, #09519d 27%, #09306b 27%, #09306b 32%, #9fcbe1 32%, #9fcbe1 37%, #deebf7 37%, #deebf7 43%, #08306b 43%, #08306b 48%, #c6dbf0 48%, #c6dbf0 53%, #fde0d2 53%, #fde0d2 58%, #69acd6 58%, #69acd6 64%, #deeaf6 64%, #deeaf6 69%, #c6dbef 69%, #c6dbef 74%, #e7dedd 74%, #e7dedd 79%, #fdbba1 79%, #fdbba1 85%, #d22424 85%, #d22424 90%, #68000d 90%, #68000d 95%, #a60f16 95%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#68000d"
    },
    "livery-2435": {
        "background": "linear-gradient(180deg, #e5e8f1 5%, #f9f9f1 5%, #f9f9f1 20%, #cd563d 20%, #cd563d 55%, #f9f9f1 55%, #f9f9f1 60%, #cd563d 60%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2437": {
        "background": "linear-gradient(300deg, #4d30a2 28%, #0000 28%, #0000 72%, #d5137e 20%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #EBF1FD 31%, #978aad 31%, #978aad 39%, #EBF1FD 39%)"
    },
    "livery-2438": {
        "background": "#FF6600",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2440": {
        "background": "#4BA0F1",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2441": {
        "background": "linear-gradient(to top, #249BED 45%, #14CBEA 45%, #14CBEA 56%, #B0B5C1 56%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2444": {
        "background": "repeating-conic-gradient(from 227deg at 78% 97%, #fff 0deg 90deg, #ca5f2b 90deg 95deg, #fff 95deg 97deg, #da5d3b 97deg 102deg, #fff 102deg 360deg)"
    },
    "livery-2445": {
        "background": "linear-gradient(180deg, #fff 50%, #502d98 50%)",
        "stroke": "#FFFFFF"
    },
    "livery-2446": {
        "background": "#028fd1",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2447": {
        "background": "radial-gradient(ellipse at 20% 134%, #c0c0c0 30%, transparent 30%), radial-gradient(ellipse at 51% 16%, #020202 60%, transparent 0%), linear-gradient(80deg, #020202 0%, #020202 31%, transparent 10%), radial-gradient(circle at 59% 20%, #FEDB34 0%, #FEDB34 50%, transparent 20%), radial-gradient(ellipse at 50% 16%, #020202 60%, transparent 10%), radial-gradient(ellipse at 50% 16%, #c0c0c0 60%, #c0c0c0 0%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#020202"
    },
    "livery-2449": {
        "background": "linear-gradient(to right, #73d702 60%, #0000 60%), linear-gradient(120deg, #0000 67.5%, #fff 67.5%, #fff 77.5%, #0000 77.5%), linear-gradient(60deg, #005bb2 65%, #fff 65%, #fff 75%, #005bb2 75%)",
        "stroke": "#FFFFFF"
    },
    "livery-2452": {
        "background": "linear-gradient(to top, #3e6eac 30%, transparent 10%), radial-gradient(circle at top left, #fff 65%, #3e6eac 50%)"
    },
    "livery-2454": {
        "background": "radial-gradient(circle at left, #ffffff 70%, #8c704e 70%, #8c704e 80%, #000000 80%)"
    },
    "livery-2455": {
        "background": "#002e5a",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2456": {
        "background": "linear-gradient(to top, #6395B6 0%, #E7EBF5 80%)"
    },
    "livery-2457": {
        "background": "#FF2222",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2458": {
        "background": "#444444",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2460": {
        "background": "linear-gradient(to right, #2F7B23 50%, #CAAE69 50%, #CAAE69 67%, #2F7B23 67%, #2F7B23 84%, #CAAE69 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2462": {
        "background": "linear-gradient(100deg, #a2dc4b 40%, #fff 40%, #fff 60%, #925ba5 60%)"
    },
    "livery-2463": {
        "background": "linear-gradient(to top, #ab2119 20%, transparent 10%), radial-gradient(circle at top left, #fff 65%, #ab2119 65%)",
        "stroke": "#ffffff"
    },
    "livery-2465": {
        "background": "radial-gradient(circle at 72% 30%, #92c7e6 42%, #0000 42%), radial-gradient(circle at 50% 5%, #a5c19e 15%, transparent 15%), radial-gradient(circle at 98% 5%, #C9DAEA 15%, transparent 15%), radial-gradient(circle at 80% 30%, #2eb171 37.5%, #1d482d 37.5%, #1d482d 45%, #a5c19e 45%)"
    },
    "livery-2466": {
        "background": "#db4a2d",
        "stroke": "#FFFFFF"
    },
    "livery-2468": {
        "background": "linear-gradient(120deg, #ff2925 67%, #000000 67%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2469": {
        "background": "linear-gradient(to top, #07014a 20%, transparent 20%), radial-gradient(at top left, #fff 70%, #07014a 70%)"
    },
    "livery-2470": {
        "background": "linear-gradient(180deg, #1175ce 15%, #48c02e 15%, #48c02e 50%, #0000 50%), linear-gradient(135deg, #48c02e 65%, #fff 65%, #fff 82%, #48c02e 82%)"
    },
    "livery-2471": {
        "background": "linear-gradient(to top, #415161 20%, #0000 20%), radial-gradient(at top left, #fff 70%, #415161 70%)"
    },
    "livery-2472": {
        "background": "linear-gradient(300deg, #8b001d 28%, #0000 28%), linear-gradient(to top, #ed1d23 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #f7941e 31%, #f7941e 39%, #0000 39%), #ed1d23",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2473": {
        "background": "linear-gradient(180deg, #1175ce 15%, #48c02e 15%, #48c02e 50%, #0000 50%), linear-gradient(135deg, #48c02e 65%, #fff 65%, #fff 82%, #48c02e 82%)"
    },
    "livery-2507": {
        "background": "#E20303",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2510": {
        "background": "linear-gradient(60deg, #1fac9e 35%, #d3d3d3 35.1% 39%, #fff 39.1% 43%, #1fac9e 43.1% 47%, #000 47.1%)",
        "color": "#ffffff",
        "fill": "#ffffff",
        "stroke": "#000000"
    },
    "livery-2512": {
        "background": "linear-gradient(to top, #f2dfc7 12%, #ff9962 12%, #ff9962 24%, #f2dfc7 24%, #f2dfc7 30%, #DE8E45 30%, #DE8E45 42%, #f2dfc7 42%)"
    },
    "livery-2513": {
        "background": "#f2dfc7"
    },
    "livery-2514": {
        "background": "radial-gradient(circle at top right, #fff 45%, #3a2a8c 45%, #3a2a8c 60%, #0000 60%), linear-gradient(180deg, #3a2a8c 25%, #fff 25%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2515": {
        "background": "linear-gradient(to top, #b3b4b5 17%, #0114e1 17%, #0114e1 25%, #01cffb 25%, #01cffb 34%, #b3b4b5 34%)",
        "stroke": "#a0a4ad"
    },
    "livery-2516": {
        "background": "linear-gradient(180deg, #fff 50%, #3a2a8c 50%, #3a2a8c 60%, #fff 60%, #fff 65%, #3a2a8c 65%, #3a2a8c 75%, #fff 75%)",
        "stroke": "#FFFFFF"
    },
    "livery-2520": {
        "background": "linear-gradient(70deg, #0000 65%, #23384e 65%), linear-gradient(180deg, #23384e 35%, #e55c16 35%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2521": {
        "background": "linear-gradient(to right, #fa260c 10%, #ffffff 10%, #ffffff 50%, #fa260c 50%, #fa260c 70%, #ffffff 70%, #ffffff 90%, #fa260c 90%)"
    },
    "livery-2522": {
        "background": "linear-gradient(to right, #FD7927 40%, #1443CD 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2523": {
        "background": "conic-gradient(from 270deg at 99.4% 42%, #152c2a 90deg, #0000 90deg), radial-gradient(at 35% 177%, #247356 39%, transparent 31%), radial-gradient(at 31% 176%, #e4f6ea 39%, transparent 31%), conic-gradient(from -173deg, #152c2a 180deg, #0000 180deg), radial-gradient(circle at 64.4% 39.5%, #152c2a 46%, #152c2a00 31%), radial-gradient(circle at 66.8% 46%, #e4f6ea 43%, #247356 31%), linear-gradient(to top, #0000 0% 100%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2526": {
        "background": "linear-gradient(to top, #11446d 20%, transparent 20%), radial-gradient(circle at top left, transparent 60%, #11446d 60% 70%, #563495 70%), radial-gradient(circle at bottom center, #fff 84%, #11446d 84% 92%, #11446d 92%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#11446d"
    },
    "livery-2527": {
        "background": "linear-gradient(to right, #fb373e 10%, #ffffff 10%, #ffffff 46%, #fb373e 46%, #fb373e 64%, #ffffff 64%, #ffffff 91%, #fb373e 91%)",
        "stroke": "#ffffff"
    },
    "livery-2528": {
        "background": "#008a26",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2529": {
        "background": "#2f4d8b",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2531": {
        "background": "radial-gradient(ellipse at 35% -45%, #385faa 45%, transparent 45%), linear-gradient(to top, #0F6DB4 20%, transparent 20%), radial-gradient(circle at top left, #fff 60%, #F79F48 60%, #F79F48 70%, #EA2639 70%)",
        "stroke": "#FFFFFF"
    },
    "livery-2533": {
        "background": "linear-gradient(65deg, #0000 50%, #c0c0c2 50%, #c0c0c2 60%, #0000 60%, #0000 65%, #2aa497 65%, #2aa497 75%, #0000 75%), linear-gradient(125deg, #f9ff0d 25%, #024a99 25%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2535": {
        "background": "#151922",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2536": {
        "background": "#FF5F1F",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2569": {
        "background": "radial-gradient(ellipse at 23% 140%, #C71A26 31%, transparent 31%), radial-gradient(circle at 51% 42%, #F3F1E5 49%, transparent 0%), linear-gradient(109deg, #F3F1E5 1%, #F3F1E5 46%, transparent 10%), linear-gradient(3deg, #C71A26 20%, #0000 20%), radial-gradient(circle at 45% 24%, #2B3F8A 60%, transparent 10%), linear-gradient(to top, #C71A26 20%, #C71A26 20%)",
        "stroke": "#F3F1E5"
    },
    "livery-2570": {
        "background": "radial-gradient(ellipse at 23% 140%, #C71A26 31%, transparent 31%), radial-gradient(circle at 51% 42%, #F3F1E5 49%, transparent 0%), linear-gradient(109deg, #F3F1E5 1%, #F3F1E5 46%, transparent 10%), linear-gradient(3deg, #C71A26 20%, #0000 20%), radial-gradient(circle at 45% 24%, #2B3F8A 60%, transparent 10%), linear-gradient(to top, #C71A26 20%, #C71A26 20%)",
        "stroke": "#F3F1E5"
    },
    "livery-2573": {
        "background": "#5c6270",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2574": {
        "background": "linear-gradient(to top, #a24181 30%, transparent 20%, transparent 95%, #a24181 95%), radial-gradient(circle at top left, #ffffff 70%, #a24181 70%)",
        "stroke": "#ffffff"
    },
    "livery-2575": {
        "background": "linear-gradient(135deg, #017a2d 40%, #a9b1b7 40%, #a9b1b7 57%, transparent 57%), linear-gradient(to top, #017a2d 17%, transparent 17%, transparent 35%, #a9b1b7 35%), linear-gradient(135deg, #017a2d 40%, #a9b1b7 40%, #a9b1b7 57%, #614ab3 57%, #614ab3 75%, #017a2d 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2576": {
        "background": "linear-gradient(45deg, #20491c 30%, transparent 30%), linear-gradient(to top, #20491c 30%, #ECE9D3 30%)",
        "stroke": "#ECE9D3"
    },
    "livery-2577": {
        "background": "linear-gradient(45deg, #213d8f 30%, #0000 30%), linear-gradient(to top, #213d8f 30%, #ECE9D3 30%)",
        "stroke": "#ECE9D3"
    },
    "livery-2579": {
        "background": "radial-gradient(circle at 90% 50%, #d15e0a 10%, transparent 10%), linear-gradient(135deg, #017a2d 40%, #a9b1b7 40%, #a9b1b7 57%, transparent 57%), linear-gradient(to top, #017a2d 17%, transparent 17%, transparent 35%, #a9b1b7 35%), linear-gradient(135deg, #017a2d 40%, #a9b1b7 40%, #a9b1b7 57%, #614ab3 57%, #614ab3 75%, #017a2d 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2580": {
        "background": "linear-gradient(115deg, #0000 70%, #0db1ea 70%, #0db1ea 76%, #f7f8fa 76%, #f7f8fa 80%, #a64189 80%), linear-gradient(65deg, #0000 70%, #0db1ea 70%), #f7f8fa",
        "stroke": "#f7f8fa"
    },
    "livery-2581": {
        "background": "linear-gradient(135deg, #017a2d 40%, #a9b1b7 40%, #a9b1b7 57%, transparent 57%), linear-gradient(to top, #017a2d 17%, transparent 17%, transparent 35%, #a9b1b7 35%), linear-gradient(135deg, #017a2d 40%, #a9b1b7 40%, #a9b1b7 57%, #eabd3d 57%, #eabd3d 60%, #244b93 60%, #244b93 75%, #017a2d 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2582": {
        "background": "#0C1E8E",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2586": {
        "background": "linear-gradient(90deg, #6e2447 50%, #0000 50%), linear-gradient(180deg, #fff 66%, #4476ce 66%)",
        "stroke": "#FFFFFF"
    },
    "livery-2587": {
        "background": "linear-gradient(to right, #FFA500 20%, #339c5e 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2588": {
        "background": "linear-gradient(to top, #a91e33 25%, #fff 25%, #fff 55%, #a91e33 55%, #a91e33 75%, #fff 75%)",
        "stroke": "#ffffff"
    },
    "livery-2590": {
        "background": "linear-gradient(to left, #b52362 50%, #0000 50%), radial-gradient(circle at center, #b52362 58%, #981b4d 58%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2591": {
        "background": "linear-gradient(to right, #CCCCCC 14%, #9A5C47 14%, #9A5C47 23%, #4C3E3D 23%, #4C3E3D 28%, #9A5C47 28%, #9A5C47 46%, #4C3E3D 46%, #4C3E3D 55%, #9A5C47 55%, #9A5C47 64%, #4C3E3D 64%, #4C3E3D 69%, #9A5C47 69%, #9A5C47 78%, #4C3E3D 78%, #4C3E3D 87%, #CCCCCC 87%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2592": {
        "background": "linear-gradient(180deg, #d5e6ee 50%, #d03c3a 50%)"
    },
    "livery-2595": {
        "background": "linear-gradient(60deg, #0000 40%, #fff 40%, #fff 42%, #8B0E04 42%, #8B0E04 45%, #b49862 45%, #b49862 47%, #fff 47%, #fff 63%, #b49862 63%, #b49862 65%, #8B0E04 65%, #8B0E04 68%, #fff 68%, #fff 70%, #fff032 70%), linear-gradient(to top, #fff 20%, #0000 20%, #0000 90%, #fff032 90%), linear-gradient(to right, #fff032 7%, #fff 7%)",
        "stroke": "#ffffff"
    },
    "livery-2598": {
        "background": "#fff387"
    },
    "livery-2599": {
        "background": "radial-gradient(circle at -40% 25%, #fff 50%, #61615e 50%, #61615e 60%, #478989 60%, #478989 70%, #fff 70%)",
        "stroke": "#ffffff"
    },
    "livery-2603": {
        "background": "linear-gradient(to top, #FFFFFF 35%, #0000 35%), linear-gradient(35deg, #FFFFFF 40%, #C0C0C0 40%, #C0C0C0 50%, #FFFFFF 50%)"
    },
    "livery-2610": {
        "background": "linear-gradient(to right, #27aedd 34%, #ee4d31 34%, #ee4d31 67%, #0000ff 67%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2611": {
        "background": "linear-gradient(135deg, #D1C8BE 34%, #CE0A12 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2613": {
        "background": "linear-gradient(180deg, #e5e6e8 20%, #f6d891 20%, #f6d891 40%, #a3e3ed 40%, #a3e3ed 55%, #cdc9c6 55%, #cdc9c6 70%, #b95259 70%, #b95259 90%, #80c0c6 90%)"
    },
    "livery-2615": {
        "background": "linear-gradient(to right, #ef508a 75%, #29367c 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2616": {
        "background": "linear-gradient(to right, #34C624 34%, #FFF544 34%, #FFF544 45%, #34C624 45%)"
    },
    "livery-2617": {
        "background": "linear-gradient(to right, #32bafc 63%, #edad32 63%, #edad32 75%, #32bafc 75%, #32bafc 88%, #edad32 88%)"
    },
    "livery-2618": {
        "background": "#87CEEB"
    },
    "livery-2621": {
        "background": "#26aae2",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2623": {
        "background": "linear-gradient(180deg, #ffffff 38%, #fd2d3a 38%, #fd2d3a 50%, #1b7b2f 50%)",
        "stroke": "#ffffff"
    },
    "livery-2626": {
        "background": "linear-gradient(260deg, #c02927 13%, #3a72d2 13%, #3a72d2 25%, #debd40 25%, #debd40 38%, #6ab479 38%, #6ab479 50%, #c02927 50%, #c02927 63%, #3a72d2 63%, #3a72d2 75%, #c7b052 75%, #c7b052 88%, #6ab479 88%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2637": {
        "background": "linear-gradient(to top, #ffffff 14%, #e30106 14%, #e30106 27%, #ffffff 27%, #ffffff 60%, #8E959B 60%, #8E959B 67%, #ffffff 67%)",
        "stroke": "#ffffff"
    },
    "livery-2639": {
        "background": "linear-gradient(to bottom, #ff0000 43%, #ffffff 43%, #ffffff 58%, #40b751 58%)",
        "stroke": "#ffffff"
    },
    "livery-2640": {
        "background": "radial-gradient(circle at right, #0000 45%, #c0c0c0 45%), linear-gradient(180deg, #5a7588 50%, #7CFC00 50%)",
        "stroke": "#FFFFFF"
    },
    "livery-2642": {
        "background": "#c6c6c9"
    },
    "livery-2643": {
        "background": "#4c4f57",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2646": {
        "background": "linear-gradient(180deg, #ffffff 75%, #48724a 75%)"
    },
    "livery-2648": {
        "background": "linear-gradient(to right, #34C624 34%, #FFF544 34%, #FFF544 45%, #34C624 45%)"
    },
    "livery-2653": {
        "background": "#FF2222",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#ff2222"
    },
    "livery-2656": {
        "background": "linear-gradient(to right, #85CE1E 10%, #ffffff 10%, #ffffff 50%, #1f1e03 50%, #1f1e03 60%, #9ecc61 60%, #9ecc61 70%, #ffffff 70%, #ffffff 90%, #EDAEC0 90%)"
    },
    "livery-2658": {
        "background": "#2fd5c7",
        "color": "#000000",
        "fill": "#000000"
    },
    "livery-2659": {
        "background": "repeating-conic-gradient(from 270deg at 30% 88%, #abea00 0deg 135deg, #0000 20deg 3360deg), linear-gradient(to top, #0000 20%, #008673 20% 21%, #abea00 21% 22%, #008673 22% 23%, #abea00 23% 24%, #008673 24% 25%, #abea00 25% 26%, #008673 26% 27%, #abea00 27% 28%, #008673 28% 29%, #0000 29%), repeating-conic-gradient(from 270deg at 5% 100%, #abea00 0deg 135deg, #0000 20deg 3360deg), linear-gradient(to top, #008673 12%, #abea00 12%)"
    },
    "livery-2660": {
        "background": "linear-gradient(to top, #555354 45%, #303ba7 45%, #303ba7 75%, #555354 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2661": {
        "background": "radial-gradient(circle at top left, #0000 75%, #4085c0 75%), linear-gradient(180deg, #fdf9ee 75%, #4085c0 75%)"
    },
    "livery-2662": {
        "background": "linear-gradient(to top, #ffffff 23%, #7d7d7d 23%, #7d7d7d 30%, #ffffff 30%, #ffffff 33%, #bf2c2c 33%, #bf2c2c 39%, #ffffff 39%)"
    },
    "livery-2663": {
        "background": "#F7B205"
    },
    "livery-2664": {
        "background": "linear-gradient(300deg, #cc2e25 28%, #0000 28%), linear-gradient(to top, #000 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #cc2e25 31%, #cc2e25 39%, #0000 39%), linear-gradient(to top, #000 60%, #0000 60%), linear-gradient(300deg, #000 80%, #cc2e25 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2665": {
        "background": "linear-gradient(180deg, #ece5c9 75%, #1e2a16 75%)"
    },
    "livery-2666": {
        "background": "linear-gradient(180deg, #fff 40%, #111111 40%, #111111 47.5%, #656565 47.5%, #656565 55%, #111111 55%, #111111 62.5%, #ffffff 62.5%)",
        "stroke": "#ffffff"
    },
    "livery-2668": {
        "background": "linear-gradient(135deg, #d62932 25%, transparent 25%), linear-gradient(to top, #d62932 20%, #e9d7b5 20%, #e9d7b5 95%, #d62932 95%)"
    },
    "livery-2669": {
        "background": "#211351",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2672": {
        "background": "linear-gradient(120deg, #0000 25%, #646571 25%, #646571 35%, #32bcee 35%, #32bcee 45%, #4d5a6d 45%), linear-gradient(180deg, #32bcee 45%, #646571 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2673": {
        "background": "linear-gradient(to left, #9cc31c 50%, transparent 50%), radial-gradient(circle at center, #9cc31c 58%, #38a203 58%)",
        "stroke": "#9cc31c"
    },
    "livery-2674": {
        "background": "linear-gradient(to top, #125c53 20%, #d52833 20%, #d52833 25%, #b5cf88 25%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2677": {
        "background": "linear-gradient(to right, #27a0df 20%, #6D8696 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2712": {
        "background": "linear-gradient(to right, #079fe6 55%, #fff 55%, #fff 65%, #079fe6 65%, #079fe6 80%, #fff 80%, #fff 90%, #079fe6 90%)"
    },
    "livery-2713": {
        "background": "linear-gradient(to right, #fa3b10 25%, #ffffff 25%, #ffffff 50%, transparent 50%), linear-gradient(to top, #ffffff 34%, #0988d5 34%, #0988d5 67%, #ffffff 67%)",
        "stroke": "#ffffff"
    },
    "livery-2714": {
        "background": "linear-gradient(125deg, #3eb4ff 30%, #0083d7 36%, #0083d7 60%, #2d3677 66%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2715": {
        "background": "radial-gradient(circle at 80% 50%, #30afa4 40%, #666666 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2717": {
        "background": "linear-gradient(to top, #015534 25%, #f1e182 25%, #f1e182 43%, #ea150e 43%, #ea150e 50%, #015534 50%, #015534 75%, #f1e182 75%)",
        "stroke": "#f1e182"
    },
    "livery-2718": {
        "background": "linear-gradient(to top, #d20808 30%, #f6dd9d 30%, #f6dd9d 50%, #d20808 50%, #d20808 57%, #f6dd9d 57%, #f6dd9d 73%, #d20808 73%, #d20808 80%, #f6dd9d 80%)",
        "stroke": "#f6dd9d"
    },
    "livery-2719": {
        "background": "linear-gradient(to top, #000000 15%, #CC3333 15%, #CC3333 65%, #fff 65%, #fff 90%, #CC3333 90%)",
        "stroke": "#ffffff"
    },
    "livery-2720": {
        "background": "linear-gradient(to top, #ffffff 25%, #5589C3 25%, #5589C3 50%, #ffffff 50%)"
    },
    "livery-2721": {
        "background": "#2a6b31",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2722": {
        "background": "linear-gradient(to top, #1B4D3E 25%, #F9E9C3 25%, #F9E9C3 50%, #1B4D3E 50%, #1B4D3E 75%, #F9E9C3 75%)",
        "stroke": "#F9E9C3"
    },
    "livery-2723": {
        "background": "linear-gradient(to top, #00296e 20%, transparent 20%), radial-gradient(circle at top left, #ff0000 60%, #F79F48 60%, #F79F48 70%, #0088ff 70%)",
        "stroke": "#ffffff"
    },
    "livery-2724": {
        "background": "linear-gradient(to top, #2a5d9e 20%, #da6e47 20%, #da6e47 40%, #ffffff 40%, #ffffff 80%, #2a5d9e 80%)"
    },
    "livery-2726": {
        "background": "linear-gradient(to top, #6c2a2a 20%, #de2f2a 20%, #de2f2a 25%, #e8d6ab 25%, #e8d6ab 50%, #6c2a2a 50%, #6c2a2a 70%, #de2f2a 70%, #de2f2a 75%, #e8d6ab 75%)",
        "stroke": "#e8d6ab"
    },
    "livery-2727": {
        "background": "linear-gradient(to top, #0d3879 50%, #959fad 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2728": {
        "background": "linear-gradient(to top, #97989d 7%, #de2f2a 7%, #de2f2a 55%, #e8d6ab 55%, #e8d6ab 93%, #6c2a2a 93%)"
    },
    "livery-2729": {
        "background": "linear-gradient(to top, #00296e 20%, transparent 20%), radial-gradient(circle at top left, #ff0000 60%, #F79F48 60%, #F79F48 70%, #0088ff 70%)",
        "stroke": "#ffffff"
    },
    "livery-2730": {
        "background": "linear-gradient(115deg, #68B801 29%, #FFFFFF 29%, #FFFFFF 72%, #42127B 72%)",
        "stroke": "#ffffff"
    },
    "livery-2731": {
        "background": "linear-gradient(to top, #2d7a79 34%, #E9A804 34%)"
    },
    "livery-2732": {
        "background": "linear-gradient(to top, #DD0000 34%, #FFEFBD 34%, #FFEFBD 50%, #DD0000 50%, #DD0000 67%, #FFEFBD 67%)"
    },
    "livery-2733": {
        "background": "linear-gradient(to top, #fe2208 50%, #000000 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2734": {
        "background": "radial-gradient(circle at 50% 45%, #C9DAEA 60%, #edf1f4 40%)"
    },
    "livery-2735": {
        "background": "linear-gradient(to right, #89919c 54%, #fcb155 54%, #fcb155 70%, #ab4d68 70%)"
    },
    "livery-2738": {
        "background": "linear-gradient(#fff 30%,#fc6d01 30% 85%,#63331f 85%)"
    },
    "livery-2739": {
        "background": "linear-gradient(to top, #1b66c2 34%, #fce803 34%)"
    },
    "livery-2740": {
        "background": "linear-gradient(to top, #ffd600 33%, #162230 33%, #162230 50%, #ffd600 50%)",
        "stroke": "#ffd600"
    },
    "livery-2741": {
        "background": "linear-gradient(45deg, #fed202 45%, #ffffff 45%, #ffffff 55%, #fa7502 55%)"
    },
    "livery-2742": {
        "background": "linear-gradient(300deg, #0000 72%, #009eda 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #048c7f 31%, #048c7f 39%, #0000 39%), #EBF1FD",
        "stroke": "#EBF1FD"
    },
    "livery-2743": {
        "background": "linear-gradient(110deg, #ffffff 40%, #f7a14f 40%, #f7a14f 45%, #ffffff 45%, #ffffff 50%, #d43a3c 50%)",
        "stroke": "#ffffff"
    },
    "livery-2744": {
        "background": "linear-gradient(to top, #49b37e 50%, #9ea4ae 50%)"
    },
    "livery-2747": {
        "background": "linear-gradient(115deg, #ffffff 65%, #af8599 65%, #af8599 68%, #ffffff 68%, #ffffff 70%, #95368e 70%)"
    },
    "livery-2748": {
        "background": "linear-gradient(75deg, #e4882c 30%, #ffda18 36%, #ffda18 66%, #19232f 66%, #19232f 76%, #455469 80%)",
        "stroke": "#ffda18"
    },
    "livery-2749": {
        "background": "linear-gradient(115deg, #04a0f7 66%, #3356a5 66%)"
    },
    "livery-2750": {
        "background": "linear-gradient(to top, #f1d66f 25%, #cd0525 25%, #cd0525 70%, #f1d66f 70%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2751": {
        "background": "linear-gradient(to right, #07c4ff 10%, #ffffff 10% 50%, #07c4ff 50% 60%, #07c4ff 60% 70%, #ffffff 70% 90%, #07c4ff 90%)",
        "stroke": "#ffffff"
    },
    "livery-2754": {
        "background": "linear-gradient(to top, #4f7c34 20%, #ffffff 20%, #ffffff 25%, #d4260e 25%, #d4260e 30%, #ffffff 30%, #ffffff 80%, #4f7c34 80%)",
        "stroke": "#ffffff"
    },
    "livery-2755": {
        "background": "linear-gradient(280deg, #6b7173 40%, #b0c0c6 40%)",
        "stroke": "#b0c0c6"
    },
    "livery-2758": {
        "background": "linear-gradient(115deg, #dfd8d8 67%, #3782a6 67%)"
    },
    "livery-2759": {
        "background": "#371F76",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2761": {
        "background": "linear-gradient(to top, #0732D9 25%, #FFFFFF 25%)"
    },
    "livery-2764": {
        "background": "linear-gradient(to top, #b6bdc5 38%, #f06d97 38%, #f06d97 50%, #b6bdc5 50%)"
    },
    "livery-2769": {
        "background": "linear-gradient(to top, #fdf2ea 10%, transparent 10%, transparent 80%, #fdf2ea 80%), radial-gradient(ellipse at 92% 30%, #2A7A1A 10%, transparent 10%), radial-gradient(ellipse at 92% 40%, #2A7A1A 10%, transparent 10%), radial-gradient(ellipse at 88% 40%, #2A7A1A 10%, transparent 10%), radial-gradient(circle at 55% 35%, #2A7A1A 50%, #57BC32 50%, #57BC32 57%, transparent 57%), linear-gradient(to left, #2A7A1A 50%, #fdf2ea 50%)",
        "color": "#fdf2ea",
        "fill": "#fdf2ea",
        "stroke": "#2A7A1A"
    },
    "livery-2770": {
        "background": "linear-gradient(to top, #fdf2ea 10%, transparent 10%, transparent 80%, #fdf2ea 80%), radial-gradient(ellipse at 92% 30%, #0170ab 10%, transparent 10%), radial-gradient(ellipse at 92% 40%, #0170ab 10%, transparent 10%), radial-gradient(ellipse at 88% 40%, #0170ab 10%, transparent 10%), radial-gradient(circle at 55% 35%, #0170ab 50%, #0db2f3 50%, #0db2f3 57%, transparent 57%), linear-gradient(to left, #0170ab 50%, #fdf2ea 50%)",
        "color": "#fdf2ea",
        "fill": "#fdf2ea",
        "stroke": "#0170ab"
    },
    "livery-2772": {
        "background": "linear-gradient(to top, #FFC73A 40%, #fff1e0 40%, #fff1e0 80%, #FFC73A 80%)"
    },
    "livery-2773": {
        "background": "linear-gradient(to right, #0055A5, 7.5%, transparent 7.5%, transparent 7.5%), linear-gradient(110deg, #ED1B23 55%, #ffcf31 55%, #ffcf31 64%, #ffffff 64%, #ffffff 73%, #062591 73%)",
        "stroke": "#ffffff"
    },
    "livery-2774": {
        "background": "linear-gradient(90deg, #9c2 45%, #06c 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2776": {
        "background": "linear-gradient(to top, #f5e6b8 12%, #e71810 12%, #e71810 50%, #f5e6b8 50%, #f5e6b8 80%, #e71810 80%)",
        "stroke": "#f5e6b8"
    },
    "livery-2777": {
        "background": "linear-gradient(180deg, #eef1da 38%, #307838 38%, #307838 50%, #eef1da 50%)"
    },
    "livery-2778": {
        "background": "linear-gradient(to top, #7a7a78 20%, #ffffff 20%, #ffffff 80%, #f57c14 80%)"
    },
    "livery-2779": {
        "background": "linear-gradient(to top, #7a7a78 20%, #ffffff 20%)"
    },
    "livery-2781": {
        "background": "radial-gradient(ellipse at 23% 140%, #C71A26 31%, transparent 31%), radial-gradient(circle at 51% 42%, #F3F1E5 49%, transparent 0%), linear-gradient(109deg, #F3F1E5 1%, #F3F1E5 46%, transparent 10%), linear-gradient(3deg, #C71A26 20%, #0000 20%), radial-gradient(circle at 45% 24%, #2B3F8A 60%, transparent 10%), radial-gradient(circle at 53% 20%, #FFDB02 60%, transparent 10%), linear-gradient(to top, #C71A26 20%, #C71A26 20%)",
        "stroke": "#F3F1E5"
    },
    "livery-2782": {
        "background": "linear-gradient(to top, #0f3281 30%, #fff 30%, #fff 40%, #c39f7a 40%, #c39f7a 48%, #fff 48%)",
        "stroke": "#ffffff"
    },
    "livery-2783": {
        "background": "linear-gradient(to top, #98999d 40%, #000000 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2784": {
        "background": "radial-gradient(circle at 80% 50%, #ec9006 70%, #FFFF00 70%)"
    },
    "livery-2788": {
        "background": "linear-gradient(to top, #0f3281 20%, #fff 20%, #fff 25%, #f19203 25%, #f19203 40%, #fff 40%)",
        "stroke": "#ffffff"
    },
    "livery-2789": {
        "background": "linear-gradient(30deg, #D61208 45%, #e89d07 45%, #e89d07 56%, #D61208 56%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2790": {
        "background": "#ffc500"
    },
    "livery-2791": {
        "background": "linear-gradient(to top, #FFFFFF 10%, #22479B 10%, #22479B 20%, #FFFFFF 20%)"
    },
    "livery-2792": {
        "background": "linear-gradient(to top, #6b2638 20%, #e5d287 20%, #e5d287 60%, #000000 60%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2794": {
        "background": "linear-gradient(to top, #ffffff 30%, transparent 30%), linear-gradient(110deg, #ffffff 35%, #60d6d6 35%, #60d6d6 40%, #ffffff 40%, #ffffff 42%, #478989 42%, #478989 53%, #ffffff 53%, #ffffff 55%, #61615e 55%, #61615e 85%, transparent 85%)",
        "stroke": "#ffffff"
    },
    "livery-2795": {
        "background": "linear-gradient(115deg, #ffffff 55%, #141414 55%, #141414 57%, #ffffff 57%, #ffffff 61%, #141414 61%, #141414 67%, #ffffff 67%, #ffffff 71%, #d1682a 71%)",
        "stroke": "#ffffff"
    },
    "livery-2828": {
        "background": "linear-gradient(to right, #f98e14 34%, #492a75 34%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#492a75"
    },
    "livery-2829": {
        "background": "linear-gradient(300deg, #0000 72%, #3E68B1 20%), linear-gradient(300deg, #8BD3FB 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #9CE5C7 31%, #9CE5C7 39%, #0000 39%), #EBF1FD",
        "stroke": "#ebf1fd"
    },
    "livery-2830": {
        "background": "linear-gradient(to right, #e43f24 34%, #fddb06 34%)"
    },
    "livery-2831": {
        "background": "linear-gradient(to top, #ffffff 75%, #9768b4 75%)"
    },
    "livery-2832": {
        "background": "linear-gradient(to top, #698B47 20%, #EDE0C0 20%, #EDE0C0 45%, #698B47 45%)"
    },
    "livery-2834": {
        "background": "linear-gradient(110deg, #ffe212 25%, #01a650 25%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#01a650"
    },
    "livery-2835": {
        "background": "linear-gradient(to top, #ffffff 10%, #15bdee 10%, #15bdee 15%, #018ad2 17%, #018ad2 22%, #0c4796 25%, #0c4796 30%, #000000 40%, #000000 63%, #0c4796 73%, #0c4796 78%, #018ad2 81%, #018ad2 86%, #15bdee 89%, #15bdee 94%, #ffffff 94%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2836": {
        "background": "radial-gradient(at top left, transparent 75%, #026654 75%), linear-gradient(180deg, transparent 70%, #01a650 70%, #01a650 78%, #026654 78%), linear-gradient(125deg, #fddd01 60%, #01a650 60%)"
    },
    "livery-2837": {
        "background": "radial-gradient(circle at 75% -10%, #bcc2c8 25%, #ffffff 25%, #ffffff 30%, transparent 30%), radial-gradient(circle at 25% 100%, #bcc2c8 25%, #ffffff 25%, #ffffff 30%, #ec1d05 30%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#ec1d05"
    },
    "livery-2838": {
        "background": "linear-gradient(to top, #ea1d1a 30%, #ffffff 30%)"
    },
    "livery-2839": {
        "background": "linear-gradient(to top, #ea1d1a 30%, #ffffff 30%, #ffffff 35%, #fa7e30 35%, #fa7e30 45%, #ffffff 45%)",
        "stroke": "#ffffff"
    },
    "livery-2840": {
        "background": "linear-gradient(110deg, #ffe212 25%, transparent 25%), linear-gradient(to top, #01a650 50%, #8ed9ed 50%, #8ed9ed 75%, #ffffff 90%)"
    },
    "livery-2844": {
        "background": "linear-gradient(110deg, #ED1B23 64%, #005da3 64%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2845": {
        "background": "linear-gradient(to top, #5A5A5A 34%, #D3D3D3 34%)"
    },
    "livery-2847": {
        "background": "linear-gradient(45deg, #FF0000 25%, #FF0000 25%, transparent 25%), linear-gradient(to top, #FF0000 30%, #FFAD00 30%)"
    },
    "livery-2848": {
        "background": "linear-gradient(to top, #dc241f 38%, #bace00 38%, #bace00 41%, #c10c62 41%, #c10c62 44%, #f29100 44%, #f29100 47%, #009ee2 47%, #009ee2 50%, #ffffff 50%)",
        "stroke": "#ffffff"
    },
    "livery-2849": {
        "background": "linear-gradient(285deg, #dc0100 10%, #012891 10%, #012891 20%, #0000 20%), linear-gradient(to top, #012891 15%, #0000 15%), linear-gradient(285deg, #dc0100 10%, #012891 10%, #012891 20%, #ffffff 20%, #ffffff 30%, #0000 30%), linear-gradient(to top, #012891 15%, #ffffff 15%, #ffffff 30%, #dc0100 30%)",
        "stroke": "#FFFFFF"
    },
    "livery-2850": {
        "background": "linear-gradient(to top, #e73559 15%, #00B5F1 15%, #00B5F1 85%, #70eaf2 85%)"
    },
    "livery-2851": {
        "background": "radial-gradient(circle at 58% -20%, transparent 55%, #FF5F1F 55%), linear-gradient(to top, #FF5F1F 50%, #4fb3ff 50%, #4fb3ff 75%, #FF5F1F 75%)",
        "color": "#fff018",
        "fill": "#fff018"
    },
    "livery-2852": {
        "background": "linear-gradient(19deg, #20b949 33%, #e1c204 33%, #e1c204 38%, #e43543 38%, #e43543 62%, #e1c204 62%, #e1c204 67%, #355acc 67%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2853": {
        "background": "linear-gradient(to right, #34C624 34%, #FFF544 34%, #FFF544 45%, #34C624 45%)"
    },
    "livery-2854": {
        "background": "#E6BB21",
        "color": "#013E74",
        "fill": "#013E74"
    },
    "livery-2855": {
        "background": "radial-gradient(at 62% 60%, #0bd 25%, #0000 25%), radial-gradient(at 77% 52%, #C0C0C0 30%, #0000 30%), radial-gradient(at 47% 22%, #07b 63%, #0000 63%), linear-gradient(5deg, #0000 63%, #07b 63%), #C0C0C0",
        "color": "#ffffff",
        "fill": "#ffffff"
    },
    "livery-2859": {
        "background": "linear-gradient(0deg, #fff 0%, #0ab8c5 15%, #0d3564 57.5%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2862": {
        "background": "linear-gradient(to top, #353a40 10%, #7f8285 10%, #7f8285 12%, #353a40 12%, #353a40 14%, #d1682a 14%, #d1682a 23%, #353a40 23%, #353a40 25%, #7f8285 25%, #7f8285 27%, #353a40 27%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2865": {
        "background": "linear-gradient(to top, #00a827 50%, #d6d6d6 50%, #d6d6d6 75%, #ffe98a 75%)",
        "color": "#ffffff",
        "fill": "#ffffff",
        "stroke": "#00a827"
    },
    "livery-2866": {
        "background": "radial-gradient(at 62% 60%, #0bd 25%, #0000 25%), radial-gradient(at 77% 52%, #ffde3b 30%, #0000 30%), radial-gradient(at 47% 22%, #07b 63%, #0000 63%), linear-gradient(5deg, #0000 63%, #07b 63%), #ffde3b",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2867": {
        "background": "radial-gradient(at 62% 60%, #0bd 25%, #0000 25%), radial-gradient(at 77% 52%, #95e2f1 30%, #0000 30%), radial-gradient(at 47% 22%, #07b 63%, #0000 63%), linear-gradient(5deg, #0000 63%, #07b 63%), #95e2f1",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2905": {
        "background": "linear-gradient(to top, #ab0b0d 20%, #0e2ba4 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2906": {
        "background": "linear-gradient(180deg, #FBB2E7 34%, #D1C05F 34%, #D1C05F 67%, #627289 67%)"
    },
    "livery-2908": {
        "background": "linear-gradient(120deg, #1A8416 67%, #01461a 67%)",
        "color": "#C6B37F",
        "fill": "#C6B37F"
    },
    "livery-2910": {
        "background": "linear-gradient(110deg, #482584 67%, #e40513 67%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#482584"
    },
    "livery-2911": {
        "background": "linear-gradient(to right, #012F6B 10%, #ffffff 10%, #ffffff 50%, #012F6B 50%, #012F6B 60%, #C10015 60%, #C10015 70%, #ffffff 70%, #ffffff 90%, #C10015 90%)",
        "stroke": "#ffffff"
    },
    "livery-2912": {
        "background": "#c2c2c2"
    },
    "livery-2915": {
        "background": "linear-gradient(to top, #cf1d11 20%, #eddcbb 20%)"
    },
    "livery-2916": {
        "background": "linear-gradient(to top, #28642e 20%, #eddcbb 20%)"
    },
    "livery-2917": {
        "background": "linear-gradient(to top, #890e1c 35%, #f8df8b 35%, #f8df8b 75%, #890e1c 75%)",
        "stroke": "#f8df8b"
    },
    "livery-2918": {
        "background": "linear-gradient(to top, #0f8dd7 25%, #C0C0C0 25%)"
    },
    "livery-2920": {
        "background": "linear-gradient(to top, #21457b 30%, #ffffff 30%, #ffffff 80%, #21457b 80%)",
        "stroke": "#ffffff"
    },
    "livery-2922": {
        "background": "radial-gradient(circle at 50% 45%, #f00 70%, #00f 70%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2923": {
        "background": "linear-gradient(to top, #f40000 50%, #fef8b7 50%)",
        "stroke": "#fef8b7"
    },
    "livery-2924": {
        "background": "linear-gradient(245deg, #0000 55%, #36BDEA 55% 65%, #2F4269 65% 75%, #0000 75%), linear-gradient(115deg, #0000 50%, #2F4269 50% 60%, #0DB375 60% 70%, #0000 70%), #2A6FB0",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2925": {
        "background": "linear-gradient(105deg, #69d750 25%, #fff 25.5%, #fff 30%, transparent 30.5%), linear-gradient(75deg, #0179a1 43%, #fff 43.5%, #fff 48%, #1a534d 48.5%)",
        "stroke": "#ffffff"
    },
    "livery-2927": {
        "background": "linear-gradient(100deg, #0000 78%, #009879 78%), linear-gradient(to right, #0000 80%, #fff 80%), linear-gradient(to right, #07c4ff 10%, #ffffff 10% 50%, #009879 50% 60%, #07c4ff 60% 70%, #ffffff 70% 90%, #faae00 90%)",
        "stroke": "#ffffff"
    },
    "livery-2931": {
        "background": "linear-gradient(to top, #ffffff 10%, #122247 10% 63%, #ffffff 63%)",
        "stroke": "#ffffff"
    },
    "livery-2932": {
        "background": "linear-gradient(60deg, #F73344 30%, #fff 35% 45%, #014B76 50%)",
        "color": "#000000",
        "fill": "#000000",
        "stroke": "#ffffff"
    },
    "livery-2934": {
        "background": "linear-gradient(to top, #2a6b31 25%, #ffffff 25%, #ffffff 50%, #2a6b31 50%, #2a6b31 75%, #ffffff 75%)",
        "stroke": "#ffffff"
    },
    "livery-2936": {
        "background": "linear-gradient(to top, #2AB500 10%, transparent 10%, transparent 90%, #2AB500 90%), linear-gradient(60deg, #2AB500 32%, #004C31 32%, #004C31 47%, #2AB500 47%)",
        "color": "#EFEFEF",
        "fill": "#EFEFEF"
    },
    "livery-2938": {
        "background": "linear-gradient(to top, #a1b1bc 15%, transparent 15%), linear-gradient(75deg, #ffda18 60%, #19232f 60%, #19232f 70%, #455469 70%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2939": {
        "background": "linear-gradient(to right, #12509d 67%, #15a7ea 67%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2940": {
        "background": "linear-gradient(to top, #000000 15%, transparent 15%), linear-gradient(290deg, transparent 55%, #07c04b 55%, #07c04b 65%, transparent 65%), linear-gradient(to top, #000000 25%, transparent 25%), linear-gradient(290deg, transparent 42%, #adf259 42%, #adf259 50%, transparent 50%), linear-gradient(to top, #000000 50%, transparent 50%), linear-gradient(290deg, transparent 78%, #aff259 78%, #aff259 81%, #929493 81%, #929493 84%, #5d5f5c 84%), #000000",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2941": {
        "background": "linear-gradient(to top, #000000 15%, transparent 15%), linear-gradient(290deg, transparent 55%, #d42611 55%, #d42611 65%, transparent 65%), linear-gradient(to top, #000000 25%, transparent 25%), linear-gradient(290deg, transparent 42%, #e47b05 42%, #e47b05 50%, transparent 50%), linear-gradient(to top, #000000 50%, transparent 50%), linear-gradient(290deg, transparent 78%, #e47b05 78%, #e47b05 81%, #929493 81%, #929493 84%, #5d5f5c 84%), #000000",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-2943": {
        "background": "linear-gradient(#d6d6d6 0%, #d6d6d6 45%, transparent 45%, transparent 86%, #d6d6d6 50%), radial-gradient(circle at 90% 140%, transparent 81%, #d6d6d6 70%), radial-gradient(circle at 90% 140%, transparent 78%, #ffcf31 70%), radial-gradient(circle at 35% 20%, transparent 0%, transparent 86%, #d6d6d6 80%), radial-gradient(circle at 35% 20%, #ED1B23 82%, #062591 71%, #062591 90%)",
        "stroke": "#d6d6d6"
    },
    "livery-2944": {
        "background": "linear-gradient(to right, #4f5574 13%, #ffffff 13%, #ffffff 63%, #4f5574 63%, #4f5574 75%, #ffffff 75%, #ffffff 88%, #4f5574 88%)",
        "stroke": "#ffffff"
    },
    "livery-2947": {
        "background": "linear-gradient(to left, #b47447 50%, transparent 50%), radial-gradient(circle at center, #b47447 58%, #553222 58%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2948": {
        "background": "#2a62bd",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2949": {
        "background": "linear-gradient(to right, #71cbf6 38%, #ffffff 38%, #ffffff 50%, #50bbe9 50%)"
    },
    "livery-2951": {
        "background": "linear-gradient(to right, #005aed 13%, #01abff 13%, #01abff 63%, #005aed 63%, #005aed 75%, #01abff 75%, #01abff 88%, #005aed 88%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2953": {
        "background": "radial-gradient(ellipse 85% 60% at 60% 85%, #009879 25%, transparent 25%), linear-gradient(to top, #04cfa9 10%, transparent 10%), radial-gradient(ellipse 85% 105% at 10% 110%, #04cfa9 40%, transparent 40%), radial-gradient(ellipse 85% 105% at 110% 110%, #04cfa9 40%, transparent 40%), radial-gradient(ellipse 85% 105% at 65% 105%, #009879 40%, transparent 40%), linear-gradient(to top, #04cfa9 10%, #ffffff 10%)",
        "stroke": "#ffffff"
    },
    "livery-2954": {
        "background": "linear-gradient(to top, #4dd937 10%, transparent 10%, transparent 80%, #4dd937 80%), radial-gradient(ellipse at 92% 30%, #00501f 10%, transparent 10%), radial-gradient(ellipse at 92% 40%, #00501f 10%, transparent 10%), radial-gradient(ellipse at 88% 40%, #00501f 10%, transparent 10%), radial-gradient(circle at 55% 35%, #00501f 50%, #a5eb54 50%, #a5eb54 57%, transparent 57%), linear-gradient(to left, #00501f 50%, #4dd937 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#00501f"
    },
    "livery-2956": {
        "background": "linear-gradient(105deg, #da271e 35%, #f9e40c 35%, #f9e40c 39%, #da271e 39%, #da271e 43%, #f9e40c 43%, #f9e40c 76%, #da271e 76%, #da271e 80%, #f9e40c 80%, #f9e40c 84%, #da271e 84%)",
        "stroke": "#f9e40c"
    },
    "livery-2957": {
        "background": "#2c1f74",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-2958": {
        "background": "linear-gradient(90deg, transparent 33%, #e90080 33%, #e90080 36%, #ea7633 36%, #ea7633 39%, #eabb04 39%, #eabb04 42%, #c19e18 42%, #c19e18 45%, #cfd300 45%, #cfd300 48%, #55aa1b 48%, #55aa1b 51%, #4eb188 51%, #4eb188 54%, #009ca1 54%, #009ca1 57%, #09bdde 57%, #09bdde 60%, #005594 60%, #005594 63%, #5e6fdf 63%, #5e6fdf 66%, transparent 66%), linear-gradient(to top, #12121d 15%, #ffffff 15%, #ffffff 43%, #00a1fa 57%)",
        "stroke": "#ffffff"
    },
    "livery-2959": {
        "background": "linear-gradient(110deg, transparent 80%, #780121 80%), linear-gradient(to top, #780121 25%, transparent 25%), linear-gradient(110deg, transparent 75%, #ffffff 75%, #ffffff 80%), linear-gradient(to top, transparent 25%, #ffffff 25%, #ffffff 30%, #d4af37 30%, #d4af37 35%, transparent 35%), linear-gradient(110deg, #ffffff 70%, #d4af37 70%, #d4af37 75%, transparent 75%)",
        "stroke": "#ffffff"
    },
    "livery-2960": {
        "background": "repeating-conic-gradient(from 227deg at 78% 97%, #0000 0deg 90deg, #fff 90deg 95deg, #fff0 95deg 97deg, #fff 97deg 102deg, #0000 102deg 360deg), linear-gradient(235deg, #005261 45%, #4ea8a6 45%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#4ea8a6"
    },
    "livery-2996": {
        "background": "linear-gradient(to right, #07c4ff 13%, #ffffff 13%, #ffffff 63%, #07c4ff 63%, #07c4ff 75%, #ffffff 75%, #ffffff 88%, #07c4ff 88%)"
    },
    "livery-2997": {
        "background": "linear-gradient(to top, #FF0000 40%, #fff1e0 40%, #fff1e0 80%, #FF0000 80%)",
        "stroke": "#fff1e0"
    },
    "livery-2998": {
        "background": "linear-gradient(to top, #dc241f 45%, #f7ecc5 45%, #f7ecc5 55%, #dc241f 55%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#dc241f"
    },
    "livery-3000": {
        "background": "linear-gradient(to bottom, #C50B0F 16%, transparent 16%), linear-gradient(120deg, #646571 35%, #C50B0F 35%, #C50B0F 45%, #4d5a6d 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3001": {
        "background": "linear-gradient(to bottom, #32bcee 16%, transparent 16%), linear-gradient(120deg, #646571 35%, #32bcee 35%, #32bcee 45%, #4d5a6d 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3002": {
        "background": "radial-gradient(circle at 79% 120%, #72c2ad 25%, transparent 25%), linear-gradient(to top, #00816a 50%, transparent 50%), linear-gradient(to right, #feda1c 50%, transparent 50%), radial-gradient(circle at 50% -10%, #feda1c 45%, #00816a 45%)"
    },
    "livery-3003": {
        "background": "radial-gradient(circle at 0% 25%, #FFFFFF 55%, #59bfd8 65%, #FFFFFF 65%, #FFFFFF 70%, #2f8da9 80%, #0b1c36 85%)",
        "stroke": "#FFFFFF"
    },
    "livery-3004": {
        "background": "linear-gradient(to top, #8edbfb 25%, #feeea4 25%, #feeea4 50%, #8edbfb 50%, #8edbfb 75%, #feeea4 75%)"
    },
    "livery-3005": {
        "background": "linear-gradient(120deg, #0000 25%, #646571 25%, #646571 35%, #C50B0F 35%, #C50B0F 45%, #4d5a6d 45%), linear-gradient(180deg, #C50B0F 45%, #646571 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3007": {
        "background": "linear-gradient(to top, #4c4f53 20%, #dc241f 20%)",
        "color": "#ebb730",
        "fill": "#ebb730"
    },
    "livery-3009": {
        "background": "linear-gradient(to right, #EC6705 13%, #ffc001 13%, #ffc001 63%, #EC6705 63%, #EC6705 75%, #ffc001 75%, #ffc001 88%, #EC6705 88%)"
    },
    "livery-3010": {
        "background": "linear-gradient(to top, #edeae5 50%, #74d9dd 50%)"
    },
    "livery-3014": {
        "background": "linear-gradient(to top, #002a95 34%, #5ad0ff 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3015": {
        "background": "linear-gradient(to top, #520e14 20%, #efdd93 20%, #efdd93 40%, #520e14 40%, #520e14 50%, #efdd93 50%)",
        "stroke": "#efdd93"
    },
    "livery-3017": {
        "background": "linear-gradient(45deg, #fc3c25 24%, #ffffff 24%, #ffffff 31%, #fc3c25 31%, #fc3c25 47%, #ffffff 47%, #ffffff 54%, #fc3c25 54%, #fc3c25 85%, #ffffff 85%, #ffffff 93%, #fc3c25 93%)",
        "color": "#ffffff",
        "fill": "#ffffff",
        "stroke": "#fc3c25"
    },
    "livery-3019": {
        "background": "radial-gradient(circle at 75% 50%, #ffffff 28%, #ec1d25 28%)",
        "stroke": "#ffffff"
    },
    "livery-3020": {
        "background": "linear-gradient(to top, #0703d0 34%, #FFF300 34%)",
        "stroke": "#FFF300"
    },
    "livery-3022": {
        "background": "radial-gradient(circle at top, #ebd743 50%, #464644 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3024": {
        "background": "linear-gradient(300deg, #0000 72%, #ff4283 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #a9b8e3 31%, #a9b8e3 39%, #0000 39%), #EBF1FD"
    },
    "livery-3025": {
        "background": "linear-gradient(to top, #367568 34%, #f6eac8 34%)"
    },
    "livery-3026": {
        "background": "linear-gradient(to top, #ffffff 30%, transparent 30%), linear-gradient(110deg, #ffffff 33%, #dfa9ce 33%, #dfa9ce 35%, #02b0d2 35%, #02b0d2 37%, #61615e 37%, #61615e 39%, #000000 39%, #000000 41%, #FF0000 41%, #FF0000 43%, #FFA500 43%, #FFA500 45%, #FFFF00 45%, #FFFF00 47%, #02944f 47%, #02944f 49%, #0066b0 49%, #0066b0 51%, #403e92 51%, #403e92 53%, #ffffff 53%, #ffffff 55%, #61615e 55%, #61615e 85%, transparent 85%)",
        "stroke": "#ffffff"
    },
    "livery-3027": {
        "background": "linear-gradient(to right, #E0311E 60%, #fff 60% 65%, #E0311E 65% 75%, #fff 75% 80%, #E0311E 80% 89%, #fff 89% 94%, #E0311E 94%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#C82647"
    },
    "livery-3029": {
        "background": "linear-gradient(60deg, #adadad 32%, transparent 32%), linear-gradient(to top, #2e1f75 10%, transparent 10%, transparent 80%, #2e1f75 80%), linear-gradient(60deg, transparent 34%, #a65cd1 34%, #a65cd1 36%, transparent 36%, transparent 37%, #a65cd1 37%, #a65cd1 39%, transparent 39%, transparent 40%, #a65cd1 40%, #a65cd1 42%, transparent 42%, transparent 43%, #a65cd1 43%, #a65cd1 45%, transparent 45%), linear-gradient(60deg, #adadad 32%, #2e1f75 32%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#2e1f75"
    },
    "livery-3030": {
        "background": "linear-gradient(to top, #fc392d 25%, #ffffff 25%, #ffffff 30%, #25b581 30%, #25b581 50%, transparent 50%), linear-gradient(290deg, #25b581 30%, #ffffff 30%)"
    },
    "livery-3032": {
        "background": "linear-gradient(65deg, #c7f000 38%, #03c144 42%, #03c144 45%, #006a27 47%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3033": {
        "background": "linear-gradient(110deg, #CEC3B0 55%, #FFFFFF 55%, #FFFFFF 62%, #3C6A60 62%)"
    },
    "livery-3034": {
        "background": "linear-gradient(to top, #673AB7 15%, #ffffff 15% 85%, #673AB7 85%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-3035": {
        "background": "linear-gradient(to top, #6ed256 34%, #f0d375 34%)"
    },
    "livery-3036": {
        "background": "linear-gradient(to top, #ef6629 34%, #f0d375 34%)"
    },
    "livery-3037": {
        "background": "linear-gradient(to top, #af2560 34%, #f0d375 34%)"
    },
    "livery-3038": {
        "background": "linear-gradient(to top, #0397df 34%, #f0d375 34%)"
    },
    "livery-3039": {
        "background": "linear-gradient(to right, #ffffff 25%, #7503c8 25%, #7503c8 38%, #774f7c 38%, #774f7c 50%, #ffffff 50%)",
        "stroke": "#ffffff"
    },
    "livery-3040": {
        "background": "linear-gradient(to right, #ff0000 10%, #add8e6 10%)"
    },
    "livery-3041": {
        "background": "linear-gradient(130deg, #FEDC00 35%, #491A3C 35.5%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3042": {
        "background": "linear-gradient(300deg, #0000 72%, #009eda 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #FFFF00 31%, #FFFF00 39%, #0000 39%), #EBF1FD"
    },
    "livery-3043": {
        "background": "linear-gradient(to bottom, #004FFF 9%, #FF00A3 9%, #FF00A3 17%, #68B8EE 17%, #68B8EE 25%, #FAFAFA 25%, #FAFAFA 34%, #FF88DE 34%, #FF88DE 42%, #7B19E6 42%, #7B19E6 50%, #27BD20 50%, #27BD20 59%, #FFDD23 59%, #FFDD23 67%, #F98218 67%, #F98218 75%, #F91818 75%, #F91818 84%, #7D5109 84%, #7D5109 92%, #000000 92%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-3045": {
        "background": "linear-gradient(to top, #0f3281 20%, #fff 20%, #fff 25%, #ffd729 25%, #ffd729 40%, #fff 40%)",
        "stroke": "#ffffff"
    },
    "livery-3046": {
        "background": "linear-gradient(to top, #C71A26 50%, #F3F1E5 50%)"
    },
    "livery-3047": {
        "background": "linear-gradient(to right, #8e3876 13%, #dd83cb 13%, #dd83cb 63%, #8e3876 63%, #8e3876 75%, #dd83cb 75%, #dd83cb 88%, #8e3876 88%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3048": {
        "background": "linear-gradient(110deg, #4DB6FF 55%, #6DECFF 55%, #6DECFF 64%, #FFFFFF 64%, #FFFFFF 73%, #0049A6 73%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#0078CE"
    },
    "livery-3050": {
        "background": "linear-gradient(115deg, #03bff1 40%, #0f8edf 40%, #0f8edf 60%, #256ed9 70%, #2069ca 90%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3051": {
        "background": "linear-gradient(to top, #AAAAAA 80%, #424243 80%)"
    },
    "livery-3055": {
        "background": "linear-gradient(248deg, #074787 52%, #E30315 52%, #E30315 55%, #074787 55%, #074787 58%, #E30315 58%, #E30315 61%, #074787 61%, #074787 64%, #E30315 64%, #E30315 67%, #074787 67%, #074787 70%, #E30315 70%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3056": {
        "background": "linear-gradient(280deg, #6b7173 19%, #b0c0c6 19%, #b0c0c6 38%, #a28834 38%, #a28834 44%, transparent 44%), linear-gradient(to top, #ff0000 20%, #ffffff 20%)",
        "stroke": "#ffffff"
    },
    "livery-3057": {
        "background": "radial-gradient(circle at 10% 45%, #64cdc9 65%, #016273 65%)",
        "stroke": "#64cdc9"
    },
    "livery-3058": {
        "background": "linear-gradient(130deg, #6193c8 38%, #001954 38%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#043478"
    },
    "livery-3059": {
        "background": "linear-gradient(to top, #5768A0 20%, transparent 20%), linear-gradient(300deg, #5768a0 28%, #0000 28%), linear-gradient(to top, #ebf1fd 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #FFFF00 31%, #FFFF00 39%, #0000 39%), #EBF1FD"
    },
    "livery-3061": {
        "background": "linear-gradient(100deg, #FF1493 40%, #FFFFFF 40%, #FFFFFF 45%, #C8A2C8 45%)"
    },
    "livery-3062": {
        "background": "radial-gradient(circle at -20% 25%, transparent 48%, #64CDE5 48%, #64CDE5 56%, #FFFF 56%, #FFFF 62%, transparent 62%), linear-gradient(to top, #2B5D64 20%, transparent 20%), radial-gradient(circle at 0% 42%, #29BFCF 5%, #29BFCF 100%, transparent 100%)"
    },
    "livery-3063": {
        "background": "linear-gradient(to top, #8a3565 15%, #ffffff 15%, #ffffff 20%, #ee6e93 20%, #ee6e93 30%, #ffffff 30%)"
    },
    "livery-3064": {
        "background": "radial-gradient(circle at -20% 25%, #60d300 48%, transparent 48%, transparent 56%, #949fa2 56%, #949fa2 62%, #60d300 62%), linear-gradient(to bottom, #f0fa8a 15%, #ecfd89 25%, #d9f393 35%, #9ae091 45%, #98eac8 55%, #6de9dc 70%, #03d7ef 90%)"
    },
    "livery-3065": {
        "background": "#1a70f5",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3066": {
        "background": "radial-gradient(circle at -20% -25%, transparent 80%, #00a4c7 80%), linear-gradient(to bottom, #ffffff 20%, transparent 20%), radial-gradient(circle at -20% -25%, transparent 75%, #102b9b 75%, #102b9b 80%, transparent 80%), linear-gradient(to bottom, #102b9b 20%, #102b9b 30%, #ffffff 30%)",
        "stroke": "#ffffff"
    },
    "livery-3068": {
        "background": "#345178",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3100": {
        "background": "radial-gradient(circle, #FAF814 45%, #ffffff 45%)"
    },
    "livery-3102": {
        "background": "linear-gradient(100deg, #0000 25%, #C146A1 25%, #C146A1 40%, #0000 40%, #0000 60%, #C146A1 60%, #C146A1 75%, #19295C 75%), linear-gradient(188deg, #19295C 30%, #0000 30%), linear-gradient(100deg, #19295C 20%, #377afe 20%, #377afe 40%, #19295C 40%, #19295C 55%, #377afe 55%, #377afe 75%, #19295C 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3103": {
        "background": "linear-gradient(to top, #c6cbc5 10%, transparent 10%), linear-gradient(97deg, transparent 80%, #636c72 80%, #636c72 90%, #c6cbc5 90%), linear-gradient(to top, transparent 10%, #636c72 10%, #636c72 20%, #c6cbc5 20%, #c6cbc5 25%, transparent 25%), linear-gradient(97deg, transparent 65%, #88919a 65%, #88919a 75%, #c6cbc5 75%, #c6cbc5 80%, transparent 80%), linear-gradient(to top, #88919a 25%, #88919a 35%, #c6cbc5 35%)"
    },
    "livery-3105": {
        "background": "linear-gradient(to top, #104fce 25%, #fde800 25%, #fde800 75%, #104fce 75%)"
    },
    "livery-3106": {
        "background": "#4e5454",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3107": {
        "background": "linear-gradient(to right, #c94098 13%, #ffffff 13%, #ffffff 63%, #c94098 63%, #c94098 75%, #ffffff 75%, #ffffff 88%, #c94098 88%)",
        "stroke": "#ffffff"
    },
    "livery-3108": {
        "background": "linear-gradient(45deg, #fc3c25 24%, #ffffff 24%, #ffffff 31%, #73aa15 31%, #73aa15 47%, #ffffff 47%, #ffffff 54%, #73aa15 54%, #73aa15 85%, #ffffff 85%, #ffffff 93%, #fc3c25 93%)"
    },
    "livery-3109": {
        "background": "linear-gradient(110deg, transparent 70%, #c4d7e0 70%), linear-gradient(to top, #00123F 30%, #008DE7 30%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#008DE7"
    },
    "livery-3110": {
        "background": "linear-gradient(to top, #49b35d 20%, #ffffff 20%)"
    },
    "livery-3111": {
        "background": "linear-gradient(180deg, #02ae48 15%, #abeb3d 15%, #abeb3d 50%, #02ae48 50%, #02ae48 80%, #abeb3d 80%)"
    },
    "livery-3112": {
        "background": "#636c75",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3113": {
        "background": "#414246",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3114": {
        "background": "#3a3e41",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3115": {
        "background": "#0546b1",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3116": {
        "background": "linear-gradient(60deg, #ef508a 32%, transparent 32%), linear-gradient(to top, #2e1f75 10%, transparent 10%, transparent 80%, #2e1f75 80%), linear-gradient(60deg, #ef508a 32%, #2e1f75 32%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#2e1f75"
    },
    "livery-3117": {
        "background": "linear-gradient(110deg, transparent 70%, #c4d7e0 70%), linear-gradient(to top, #00123F 30%, #EB6200 30%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#EB6200"
    },
    "livery-3119": {
        "background": "linear-gradient(to top, #FFFFFF 20%, #069C7B 20%, #069C7B 40%, #FFFFFF 40%)",
        "stroke": "#FFFFFF"
    },
    "livery-3120": {
        "background": "#cc181a",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3121": {
        "background": "linear-gradient(to top, #f2ead3 37%, #1c49a2 37%, #1c49a2 46%, #f2ead3 46%, #f2ead3 82%, #1c49a2 82%)",
        "stroke": "#f2ead3"
    },
    "livery-3122": {
        "background": "linear-gradient(to top, #564499 25%, #ffffff 25%)",
        "stroke": "#ffffff"
    },
    "livery-3126": {
        "background": "#01B5B6",
        "color": "#FFE700",
        "fill": "#FFE700"
    },
    "livery-3127": {
        "background": "linear-gradient(to top, #fdf2ea 10%, transparent 10%, transparent 80%, #fdf2ea 80%), radial-gradient(ellipse at 92% 30%, #2A7A1A 10%, transparent 10%), radial-gradient(ellipse at 92% 40%, #2A7A1A 10%, transparent 10%), radial-gradient(ellipse at 88% 40%, #2A7A1A 10%, transparent 10%), radial-gradient(circle at 55% 35%, #2A7A1A 50%, #57BC32 50%, #57BC32 57%, transparent 57%), linear-gradient(to left, #2A7A1A 50%, #fdf2ea 50%)",
        "color": "#fdf2ea",
        "fill": "#fdf2ea",
        "stroke": "#2A7A1A"
    },
    "livery-3128": {
        "background": "linear-gradient(to top, #da260e 20%, #ffffff 20%, #ffffff 25%, #da260e 25%, #da260e 50%, #ffffff 50%)",
        "stroke": "#ffffff"
    },
    "livery-3129": {
        "background": "linear-gradient(to top, #ffffff 20%, #da260e 20%, #da260e 25%, #ffffff 25%, #ffffff 50%, #ffffff 50%)",
        "stroke": "#ffffff"
    },
    "livery-3130": {
        "background": "linear-gradient(to top, #ffffff 10%, #7f8285 10%, #7f8285 12%, #ffffff 12%, #ffffff 14%, #d1682a 14%, #d1682a 23%, #ffffff 23%, #ffffff 25%, #7f8285 25%, #7f8285 27%, #ffffff 27%, #ffffff 75%, #353a40 60%)",
        "stroke": "#ffffff"
    },
    "livery-3163": {
        "background": "radial-gradient(circle at 33% -39%, #ffffff 70.5%, #e31420 71%)"
    },
    "livery-3164": {
        "background": "linear-gradient(120deg, #ff0000 29%, #2191c3 29%, #2191c3 72%, #1a222c 72%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3165": {
        "background": "linear-gradient(110deg, #65BC46 55%, #FFFFFF 55%, #FFFFFF 62%, #106032 62%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-3166": {
        "background": "#f87217"
    },
    "livery-3167": {
        "background": "#87488c",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-3169": {
        "background": "linear-gradient(to top, #277bda 40%, transparent 40%), linear-gradient(120deg, #ffffff 70%, #277bda 70%)"
    },
    "livery-3170": {
        "background": "linear-gradient(60deg, #00bbff 32%, transparent 32%), linear-gradient(to top, #0088dd 10%, transparent 10%, transparent 80%, #0088dd 80%), linear-gradient(60deg, transparent 34%, #88ddff 34%, #88ddff 36%, transparent 36%, transparent 37%, #88ddff 37%, #88ddff 39%, transparent 39%, transparent 40%, #88ddff 40%, #88ddff 42%, transparent 42%, transparent 43%, #88ddff 43%, #88ddff 45%, transparent 45%), linear-gradient(60deg, #00bbff 32%, #0088dd 32%)",
        "stroke": "#0088dd"
    },
    "livery-3171": {
        "background": "linear-gradient(110deg, #cc181a 55%, #fef503 55%, #fef503 62%, #2b2b8d 62%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-3172": {
        "background": "linear-gradient(300deg, #091c63 28%, #0000 28%), linear-gradient(to top, #337ebf 15%, #0000 15%), linear-gradient(300deg, #0000 31%, #c4e2d6 31%, #c4e2d6 39%, #0000 39%), #337ebf",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#337ebf"
    },
    "livery-3173": {
        "background": "linear-gradient(to top, #004B2A 34%, #c91818 34%, #c91818 67%, #0023b2 67%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3175": {
        "background": "linear-gradient(to right, #ffffff 25%, #3ba934 25%, #3ba934 50%, #ffffff 50%)"
    },
    "livery-3176": {
        "background": "linear-gradient(to right, #c6a01d 10%, #c90908 10%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3177": {
        "background": "linear-gradient(to top, #131108 20%, #feef9a 20%)"
    },
    "livery-3178": {
        "background": "linear-gradient(to top, #21ABE8 25%, #E3E0AA 25%, #E3E0AA 50%, #21ABE8 50%, #21ABE8 70%, #E3E0AA 70%, #E3E0AA 90%, #21ABE8 90%)"
    },
    "livery-3180": {
        "background": "linear-gradient(to top, #e03c92 25%, #FFFFFF 25%)"
    },
    "livery-3181": {
        "background": "#e03c92",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3182": {
        "background": "linear-gradient(65deg, #c7f000 38%, #03c144 42%, #03c144 45%, #006a27 47%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3183": {
        "background": "radial-gradient(ellipse 133% 138% at 5% 28%, #0000 60%, #88919a 60%), radial-gradient(ellipse 130% 133% at 0% 23%, #0000 60%, #88919a 60%), #c6cbc5"
    },
    "livery-3184": {
        "background": "linear-gradient(to top, #b5d25c 20%, #ffffff 20%)"
    },
    "livery-3185": {
        "background": "linear-gradient(to top, #c72b35 20%, #f6dfa3 20%)"
    },
    "livery-3186": {
        "background": "#67a5e3"
    },
    "livery-3187": {
        "background": "linear-gradient(to top, #00a25b 25%, #f9eea3 25%)"
    },
    "livery-3188": {
        "background": "#35bb4b"
    },
    "livery-3189": {
        "background": "linear-gradient(to top, #ccccc4 20%, #3387c3 20%)"
    },
    "livery-3190": {
        "background": "linear-gradient(to top, #f9a926 20%, #ffffff 20%)"
    },
    "livery-3191": {
        "background": "#cc181a",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3192": {
        "background": "linear-gradient(to top, #3bb143 25%, #fff39a 25%, #fff39a 50%, #3bb143 50%, #3bb143 75%, #fff39a 75%)"
    },
    "livery-3195": {
        "background": "linear-gradient(to right, #960019 34%, #f8e473 34%, #f8e473 67%, #960019 67%)",
        "stroke": "#f8e473"
    },
    "livery-3196": {
        "background": "linear-gradient(to right, #FF2222 10%, #40A6BC 10%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#40A6BC"
    },
    "livery-3198": {
        "background": "linear-gradient(110deg, #cc181a 55%, #fef503 55%, #fef503 62%, #2b2b8d 62%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-3199": {
        "background": "linear-gradient(to top, #FF5F1F 45%, #07AA98 45%, #07AA98 75%, #FF5F1F 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3200": {
        "background": "linear-gradient(270deg, #ffffff 5%, #926e2e 5%, #926e2e 10%, #ffffff 10%, #ffffff 15%, #353841 15%, #353841 20%, #ffffff 20%)"
    },
    "livery-3201": {
        "background": "linear-gradient(to right, #ffffff 63%, #02bdb9 63%, #02bdb9 75%, #ffffff 75%, #ffffff 88%, #02bdb9 88%)",
        "stroke": "#ffffff"
    },
    "livery-3202": {
        "background": "radial-gradient(at bottom right, #023ebf 40%, #e7081f 40%, #e7081f 45%, #ffffff 45%)",
        "stroke": "#ffffff"
    },
    "livery-3203": {
        "background": "radial-gradient(circle at 100% 10%, #256eb1 20%, transparent 20%), radial-gradient(circle at 76% 61%, transparent 50%, #FEDC00 50%), radial-gradient(circle at 100% 60%, #256eb1 50%, #00ADEF 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3204": {
        "background": "radial-gradient(circle at 100% 10%, #256eb1 20%, transparent 20%), radial-gradient(circle at 76% 61%, transparent 50%, #cfd8de 50%), radial-gradient(circle at 100% 60%, #256eb1 50%, #00ADEF 50%)"
    },
    "livery-3205": {
        "background": "linear-gradient(310deg, transparent 40%, #FEDC00 40%, #FEDC00 45%, transparent 45%), linear-gradient(270deg, #256eb1 20%, transparent 20%), linear-gradient(310deg, #256eb1 25%, #00ADEF 25%, #00ADEF 35%, #256eb1 35%, #256eb1 40%, transparent 40%), linear-gradient(90deg, #FEDC00 50%, transparent 50%), linear-gradient(310deg, #256eb1 45%, #256eb1 50%, #FEDC00 50%)"
    },
    "livery-3206": {
        "background": "linear-gradient(310deg, transparent 40%, #cfd8de 40%, #cfd8de 45%, transparent 45%), linear-gradient(270deg, #256eb1 20%, transparent 20%), linear-gradient(310deg, #256eb1 25%, #00ADEF 25%, #00ADEF 35%, #256eb1 35%, #256eb1 40%, transparent 40%), linear-gradient(90deg, #cfd8de 50%, transparent 50%), linear-gradient(310deg, #256eb1 45%, #256eb1 50%, #cfd8de 50%)"
    },
    "livery-3207": {
        "background": "linear-gradient(310deg, transparent 40%, #6caf3b 40%, #6caf3b 45%, transparent 45%), linear-gradient(270deg, #3c735f 20%, transparent 20%), linear-gradient(310deg, #3c735f 25%, #314f4e 25%, #314f4e 35%, #3c735f 35%, #3c735f 40%, transparent 40%), linear-gradient(90deg, #6caf3b 50%, transparent 50%), linear-gradient(310deg, #3c735f 45%, #3c735f 50%, #6caf3b 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3208": {
        "background": "linear-gradient(310deg, transparent 40%, #e7081f 40%, #e7081f 45%, transparent 45%), linear-gradient(270deg, #023ebf 20%, transparent 20%), linear-gradient(310deg, #023ebf 25%, #ffffff 25%, #ffffff 35%, #023ebf 35%, #023ebf 40%, transparent 40%), linear-gradient(90deg, #e7081f 50%, transparent 50%), linear-gradient(310deg, #023ebf 45%, #023ebf 50%, #e7081f 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#023ebf"
    },
    "livery-3209": {
        "background": "linear-gradient(310deg, transparent 40%, #ffffff 40%, #ffffff 45%, transparent 45%), linear-gradient(270deg, #a2246a 20%, transparent 20%), linear-gradient(310deg, #a2246a 25%, #642b54 25%, #642b54 35%, #a2246a 35%, #a2246a 40%, transparent 40%), linear-gradient(90deg, #ffffff 50%, transparent 50%), linear-gradient(310deg, #a2246a 45%, #a2246a 50%, #ffffff 50%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-3213": {
        "background": "linear-gradient(to right, #ffffff 29%, #0D3D91 29%, #0D3D91 72%, #ffffff 72%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#0D3D91"
    },
    "livery-3214": {
        "background": "linear-gradient(to right, #6e1948 17%, #ffffff 17%, #ffffff 84%, #6e1948 84%)",
        "stroke": "#ffffff"
    },
    "livery-3215": {
        "background": "linear-gradient(180deg, #f0d714 35%, #499b4a 35%, #499b4a 80%, #0c673e 80%)"
    },
    "livery-3216": {
        "background": "linear-gradient(to top, #284889 80%, #FFD700 80%, #FFD700 87%, #284889 87%, #284889 92%, #FFD700 92%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#284889"
    },
    "livery-3217": {
        "background": "linear-gradient(110deg, transparent 70%, #c4d7e0 70%), linear-gradient(to top, #00123F 30%, #FC9900 30%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#FC9900"
    },
    "livery-3218": {
        "background": "linear-gradient(to right, #716973 20%, #B68380 20%, #B68380 40%, #79575B 40%, #79575B 60%, #8F5853 60%, #8F5853 80%, #674143 80%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3219": {
        "background": "linear-gradient(to top, #1f4299 25%, #b1b5bc 25%)"
    },
    "livery-3220": {
        "background": "#c0bfbf"
    },
    "livery-3221": {
        "background": "#DC241F",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3222": {
        "background": "linear-gradient(180deg, #e6e1d3 55%, #59824c 55%, #59824c 70%, #917432 70%, #917432 85%, #e6e1d3 85%)"
    },
    "livery-3223": {
        "background": "linear-gradient(to top, #000000 10%, #fbd316 10%, #fbd316 35%, #ffffff 35%)"
    },
    "livery-3224": {
        "background": "linear-gradient(to top, #FFFFFF 13%, #C11D30 13%, #C11D30 15%, #002679 15%, #002679 25%, #FFFFFF 25%, #FFFFFF 27%, #C11D30 27%, #C11D30 45%, #FFFFFF 45%, #FFFFFF 47%, #002679 47%, #002679 65%, #FFFFFF 65%, #FFFFFF 67%, #C11D30 67%, #C11D30 85%, #FFFFFF 85%, #FFFFFF 87%, #002679 87%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#002679"
    },
    "livery-3225": {
        "background": "radial-gradient(circle at 70% 43%, #203962 18%, transparent 19%), radial-gradient(circle at 70% 58%, #203962 18%, transparent 19%), radial-gradient(circle at 70% 50%, #203962 19%, transparent 20%), radial-gradient(circle at 71% 50%, #307bbc 30%, transparent 30%), radial-gradient(circle at 70% 36%, #307bbc 30%, transparent 30%), radial-gradient(circle at 69.5% 45%, #307bbc 30%, transparent 31%), radial-gradient(circle at 70% 54%, #307bbc 31%, transparent 30%), radial-gradient(circle at 70% 64%, #307bbc 30%, transparent 30%), linear-gradient(to right, #78c050 75%, transparent 75%), radial-gradient(circle at 70% 50%, transparent 0%, #203962 0%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#203962"
    },
    "livery-3226": {
        "background": "radial-gradient(circle at top, #12afe0 50%, #0263be 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3227": {
        "background": "linear-gradient(to top, #000000 25%, transparent 25%), linear-gradient(100deg, transparent 67%, #07c29a 67%, #07c29a 70%, transparent 70%, transparent 77%, #bfc94d 77%, #bfc94d 80%, transparent 80%, transparent 87%, #32bef7 87%, #32bef7 90%, transparent 90%), linear-gradient(to top, #000000 25%, #000000 35%, transparent 35%), linear-gradient(100deg, #000000 62%, #d22a51 62%, #d22a51 65%, #000000 65%, #000000 67%, transparent 67%, transparent 70%, #000000 70%, #000000 72%, #d9be77 72%, #d9be77 75%, #000000 75%, #000000 77%, transparent 77%, transparent 80%, #000000 80%, #000000 82%, #7040e1 82%, #7040e1 85%, #000000 85%, #000000 87%, transparent 87%, transparent 90%, #000000 90%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#000000"
    },
    "livery-3229": {
        "background": "linear-gradient(to top, #0091CB 25%, transparent 25%), radial-gradient(circle at top left, transparent 68%, #F0CC06 68%, #F0CC06 73%, #0091CB 73%), linear-gradient(to top, transparent 25%, #F0CC06 25%, #F0CC06 30%, #ED1B23 30%, #ED1B23 85%, #FFFFFF 85%)",
        "stroke": "#FFFFFF"
    },
    "livery-3232": {
        "background": "linear-gradient(to top, #007f7e 25%, #ffffff 25%)"
    },
    "livery-3233": {
        "background": "linear-gradient(to top, #d5d4d5 20%, #2967c4 20%, #2967c4 80%, #d5d4d5 80%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3234": {
        "background": "linear-gradient(110deg, #FDEC80 34%, #ECC178 34%, #ECC178 50%, #13A7CB 50%, #13A7CB 67%, #0773c5 67%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3235": {
        "background": "linear-gradient(to top, #ffffff 20%, #d5332e 20%, #d5332e 25%, #39b780 25%, #39b780 50%, #ffffff 50%)"
    },
    "livery-3236": {
        "background": "linear-gradient(to top, #256258 40%, #8add97 40%, #8add97 45%, #4fb08b 45%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3239": {
        "background": "#2080a0",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3243": {
        "background": "linear-gradient(to top, #82DD40 60%, #1188ee 60%, #1188ee 80%, #01449A 80%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3244": {
        "background": "linear-gradient(to left, #ba9955 50%, transparent 50%), radial-gradient(circle at center, #ba9955 58%, #f2b946 58%)"
    },
    "livery-3245": {
        "background": "linear-gradient(to right, #34683d 67%, #478350 67%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3246": {
        "background": "linear-gradient(to right, #f44b15 10%, #34387f 10%, #34387f 40%, #e93776 40%, #e93776 50%, #ffc41e 50%, #ffc41e 60%, #96c3e3 60%, #96c3e3 80%, #f33a79 80%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3247": {
        "background": "#FF4177",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3248": {
        "background": "linear-gradient(to right, #ffffff 25%, #d21415 25%, #d21415 50%, #ffffff 50%)"
    },
    "livery-3250": {
        "background": "linear-gradient(to right, #C5C4C0 40%, #062A63 40%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3251": {
        "background": "linear-gradient(to top, #d20c0e 10%, #a08a61 10%, #a08a61 20%, #d20c0e 20%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3252": {
        "background": "#1F3F7A",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3253": {
        "background": "linear-gradient(to top, #0f3281 20%, #fff 20%, #fff 25%, #f19203 25%, #f19203 40%, #fff 40%)",
        "stroke": "#ffffff"
    },
    "livery-3254": {
        "background": "linear-gradient(to top, #00B5F1 20%, #ffffff 20%)"
    },
    "livery-3255": {
        "background": "radial-gradient(circle at 3% 8%, #ffffff 30%, #5e6671 30.5%)",
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#5e6671"
    },
    "livery-3256": {
        "background": "repeating-conic-gradient(from 227deg at 78% 97%, #0000 0deg 90deg, #fff 90deg 95deg, #fff0 95deg 97deg, #fff 97deg 102deg, #0000 102deg 360deg), linear-gradient(235deg, #f18602 45%, #FF0000 45%)",
        "stroke": "#FFFFFF"
    },
    "livery-3258": {
        "background": "linear-gradient(to top, #a7dcee 34%, #192652 34%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3261": {
        "background": "#264baf",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3262": {
        "background": "#FFFFFF",
        "color": "#FB0000",
        "fill": "#FB0000"
    },
    "livery-3263": {
        "background": "linear-gradient(to top, #FFFFFF 10%, #2E6BF7 10%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3264": {
        "background": "linear-gradient(to top, #C2343C 10%, #122244 10%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3265": {
        "background": "linear-gradient(to left, #163069 25%, #D8AD3C 25%, #D8AD3C 75%, #163069 75%)",
        "stroke": "#FFFFFF"
    },
    "livery-3266": {
        "background": "linear-gradient(to top, #0f3281 20%, #fff 20%)"
    },
    "livery-3267": {
        "background": "#fff954"
    },
    "livery-3268": {
        "background": "linear-gradient(to top, #1d8f9b 20%, #6ec0d7 20%)"
    },
    "livery-3269": {
        "background": "linear-gradient(to top, #dc8eca 50%, #dc4998 50%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3270": {
        "background": "linear-gradient(to top, #dba74e 20%, #e1c673 20%)"
    },
    "livery-3271": {
        "background": "linear-gradient(to top, #307bca 60%, transparent 60%), linear-gradient(to left, #FF0000 20%, #ffffff 20%, #ffffff 40%, #FF0000 40%, #FF0000 60%, #ffffff 60%, #ffffff 80%, #FF0000 80%)"
    },
    "livery-3272": {
        "background": "#A3E4D7"
    },
    "livery-3273": {
        "background": "#008CD1",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3274": {
        "background": "#25a246",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3275": {
        "background": "linear-gradient(to top, #000000 10%, #dc241f 10%, #dc241f 30%, #ffffff 30%, #ffffff 50%, #dc241f 50%, #dc241f 70%, #ffffff 70%, #ffffff 90%, #c0c0c0 90%)",
        "stroke": "#ffffff"
    },
    "livery-3276": {
        "background": "linear-gradient(to top, #f4bf9a 50%, #5DADE2 50%)"
    },
    "livery-3277": {
        "background": "radial-gradient(circle at 50% 110%, #82bfeb 10%, #e29f95 10%, #e29f95 15%, #ebbba6 15%, #ebbba6 20%, #e7d3a6 20%, #e7d3a6 25%, #b3cda8 25%, #b3cda8 30%, #add4fc 30%, #add4fc 35%, #9786ca 35%, #9786ca 40%, #82bfeb 40%)"
    },
    "livery-3278": {
        "background": "linear-gradient(to right, #c800c8 15%, #0085c8 15%, #0085c8 29%, #004c73 29%, #004c73 43%, #00324b 43%, #00324b 58%, #004c73 58%, #004c73 72%, #0085c8 72%, #0085c8 86%, #c800c8 86%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3279": {
        "background": "linear-gradient(to top, #02034e 25%, #FDEE00 25%)",
        "stroke": "#FFFFFF"
    },
    "livery-3280": {
        "background": "linear-gradient(to top, #fffdd0 50%, #7F1A15 50%, #7F1A15 60%, #fffdd0 60%, #fffdd0 80%, #7F1A15 80%, #7F1A15 90%, #fffdd0 90%)",
        "stroke": "#fffdd0"
    },
    "livery-3285": {
        "background": "linear-gradient(to top, #307838 34%, #feed30 34%, #feed30 67%, #307838 67%)"
    },
    "livery-3286": {
        "background": "linear-gradient(to top, #cf1d11 25%, #a5a5a5 25%, #a5a5a5 50%, #cf1d11 50%, #cf1d11 75%, #a5a5a5 75%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3287": {
        "background": "linear-gradient(to top, #a1c616 34%, #47b8ee 34%, #47b8ee 67%, #f0c64e 67%)"
    },
    "livery-3289": {
        "background": "linear-gradient(to top, #59b3f1 30%, #b4dffa 30%)"
    },
    "livery-3290": {
        "background": "#f4eb8e"
    },
    "livery-3291": {
        "background": "linear-gradient(to top, #000000 10%, #ffffff 10%, #ffffff 15%, #447acd 15%, #447acd 60%, #ffffff 60%)"
    },
    "livery-3292": {
        "background": "linear-gradient(95deg, #0059a5 15%, #0074ad 15%, #0074ad 25%, #01779b 25%, #01779b 35%, #018996 35%, #018996 45%, #018488 50%, #039c68 55%, #039c68 60%, #74d04b 60%, #74d04b 70%, transparent 70%), linear-gradient(85deg, #74d04b 70%, #74d04b 80%, #039c68 80%, #039c68 90%, #018488 90%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3293": {
        "background": "linear-gradient(100deg, #a800ff 5%, #0054ff 5.1% 10%, #6f0 10.1% 15%, #ffd200 15.1% 20%, #ff7800 20.1% 25%, #ff0101 25.1% 30%, #ffbf00 30.1%)",
        "color": "#ffffff",
        "fill": "#ffffff",
        "border_top": "3px solid #333",
        "border_bottom": "3px solid #333",
        "height": "19px"
    },
    "livery-3294": {
        "background_color": "#ffffff",
        "background_image": "linear-gradient(-90deg, #654007ff 35%, transparent 35.05%), linear-gradient(-90deg, #e0e0e0ff 50%, transparent 50.05%)"
    },
    "livery-3299": {
        "color": "#fff",
        "fill": "#fff",
        "background": "linear-gradient(60deg, #8d7cc2 32%, #0000 32%), linear-gradient(#2d1c73 20%, #0000 20% 90%, #2d1c73 90%), linear-gradient(60deg, #0000 34%, #c9cafe 34% 36%, #0000 36% 37%, #c9cafe 37% 39%, #0000 39% 40%, #c9cafe 40% 42%, #0000 42% 43%, #c9cafe 43% 45%, #0000 45%), linear-gradient(60deg, #0bf 32%, #2d1c73 32%)"
    },
    "livery-3302": {
        "background": "linear-gradient(110deg, #fff 64%, #f26f23 64% 73%, #fff 73% 78%, #2f2d8a 78% 87%, #fff 87%)"
    },
    "livery-3303": {
        "color": "#fff",
        "fill": "#fff",
        "background": "linear-gradient(110deg, #01a9db 20%, #0000 20%), linear-gradient(360deg, #193276 30%, #0000 30%), linear-gradient(110deg, #193276 30%, #01a9db 30% 40%, #193276 40% 70%, #01a9db 70% 80%, #193276 80%)"
    },
    "livery-3317": {
        "color": "#fff",
        "fill": "#fff",
        "background": "#761a48"
    },
    "livery-3328": {
        "color": "#fff",
        "fill": "#fff",
        "background": "#1f2f6b"
    },
    "livery-3337": {
        "color": "#fff",
        "fill": "#fff",
        "background": "#7b3f7f"
    },
    "livery-3343": {
        "color": "#fff",
        "fill": "#fff",
        "stroke": "#da260e",
        "background": "linear-gradient(#da260e 75%, #fff 75% 80%, #da260e 80%)"
    },
    "livery-3370": {
        "color": "#fff",
        "fill": "#fff",
        "background": "linear-gradient(#5e6060 45%, #fe0000 45% 55%, #26272c 55%)"
    },
    "livery-3372": {
        "color": "#fff",
        "fill": "#fff",
        "background": "radial-gradient(circle at -10% -73%, #808083 76%, #0f358d 76% 81%, #88d3ff 81%)"
    },
    "livery-3374": {
        "color": "#fff",
        "fill": "#fff",
        "background": "linear-gradient(110deg, gray 64%, #f26f23 64% 73%, gray 73% 78%, #2f2d8a 78% 87%, gray 87%)"
    },
    "livery-3391": {
        "background": "linear-gradient(#fff 50%,#fdad32 50% 84%,#022660 84%)"
    },
    "livery-3400": {
        "color": "#fff",
        "fill": "#fff",
        "background": "linear-gradient(#fff 10%,#3f423f 10% 30%,#f7400c 30% 90%,#3f423f 90%)"
    },
    "livery-3402": {
        "background": "linear-gradient(#fff 50%,#fdad32 50% 84%,#552100 84%)"
    },
    "livery-3418": {
        "background": "linear-gradient(90deg,#14b3c1 50%,#0c4a69 50% 67%,#14b3c1 67% 84%,#0c4a69 84%)",
        "color": "#fff",
        "fill": "#fff"
    },
    "livery-3421": {
        "color": "#b49862",
        "fill": "#b49862",
        "stroke": "#fff",
        "background": "linear-gradient(#fff 25%, #8c0b05 25% 45%, #fff 45% 75%, #8c0b05 75%)"
    }
}

def split_gradients(css):
    parts = []
    depth = 0
    current = []

    for char in css:
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        if char == ',' and depth == 0:
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(char)

    if current:
        parts.append(''.join(current).strip())

    return parts

def normalize_hex_color(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c*2 for c in hex_color)
    if len(hex_color) != 6:
        # Fallback if invalid length
        return '#ffffff'
    return '#' + hex_color.lower()

def flip_single_gradient(gradient):
    gradient = gradient.strip()
    if gradient.startswith('linear-gradient'):
        return flip_linear_gradient(gradient)
    elif gradient.startswith('radial-gradient'):
        return flip_radial_gradient(gradient)
    return gradient

def flip_gradient_horizontally(gradient_string):
    gradients = split_gradients(gradient_string)
    flipped = [flip_single_gradient(g) for g in gradients]
    return ','.join(flipped)
    
def flip_linear_gradient(gradient):
    gradient = gradient.lower()
    angle_regex = re.compile(r'linear-gradient\(\s*([-+]?\d+\.?\d*)deg')
    match = angle_regex.search(gradient)
    if match:
        angle = float(match.group(1))
        flipped_angle = -angle
        start = match.start(1)
        end = match.end(1)
        return gradient[:start] + str(flipped_angle) + gradient[end:]
    return gradient


def flip_radial_gradient(gradient):
    gradient = gradient.lower()
    # Flip radial-gradient horizontal position (at X% Y%)
    pos_regex = re.compile(r'at\s+([-\d.]+)%\s+([-\d.]+)%')
    match = pos_regex.search(gradient)
    if match:
        x = float(match.group(1))
        y = match.group(2)
        flipped_x = 100 - x
        return pos_regex.sub(f'at {flipped_x}% {y}%', gradient)
    return gradient

def get_contrast_color(hex_color):
    """
    Returns '#000000' or '#ffffff' depending on contrast against the background color
    """
    hex_color = normalize_hex_color(hex_color).lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    # Calculate luminance
    luminance = (0.299 * r + 0.587 * g + 0.114 * b)

    # Use white text for dark backgrounds, black text for light backgrounds
    return '#000000' if luminance > 186 else '#ffffff'


def flip_gradient_horizontally(gradient):
    gradient = gradient.strip()
    if gradient.startswith('linear-gradient'):
        return flip_linear_gradient(gradient)
    elif gradient.startswith('radial-gradient'):
        return flip_radial_gradient(gradient)
    else:
        # unknown gradient type, return as is
        return gradient

def extract_first_hex_color(css_gradient):
    # Regex to find hex colors (#fff or #ffffff)
    hex_color_match = re.search(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})', css_gradient)
    if hex_color_match:
        return normalize_hex_color(hex_color_match.group(0))
    return '#000000'  # fallback black

class Command(BaseCommand):
    help = 'Import vehicle types from a CSV file and generate flipped gradients'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **kwargs):
        try:
            user = CustomUser.objects.get(username='Kai')
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR('User with ID 1 does not exist.'))
            return

        csv_file = kwargs['csv_file']

        with open(csv_file, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                original_css = row['Color'] or "black"

                livery_key = row['LiveryCSS']
                if livery_key in manual_liveries:
                    livery = manual_liveries[livery_key]
                    if 'background_image' in livery:
                        original_css = livery['background_image']
                    elif 'background' in livery:
                        original_css = livery['background']
                    elif 'background_color' in livery:
                        original_css = livery['background_color']
                    else:
                        self.stdout.write(self.style.ERROR(row['LiveryCSS']))

                original_css = original_css.lower()
                flipped_css = flip_gradient_horizontally(original_css)
                first_color = extract_first_hex_color(original_css)
                text_color = get_contrast_color(first_color)

                liverie.objects.update_or_create(
                    id=row['ID'],
                    defaults={
                        'name': row['LiveryName'] or "black",
                        'colour': first_color,
                        'left_css': original_css,
                        'right_css': flipped_css,
                        'published': row['Live'] or "black",
                        'text_colour': text_color,
                        'added_by': user,
                        'aproved_by': user,
                    }
                )

                self.stdout.write(self.style.SUCCESS('Imported livery: %s' % row['LiveryName']))

        self.stdout.write(self.style.SUCCESS('Successfully imported all liveries.'))
