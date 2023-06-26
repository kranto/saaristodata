fdata = {
  mun: {
    Eckerö: { },
    Hammarland: { },
    Geta: { },
    Finström: { },
    Saltvik: { },
    Sund: { },
    Vårdö: { },
    Jomala: { },
    Mariehamn: { name_fi: "Maarianhamina"},
    Lemland: { },
    Lumparland: { },
    Föglö: { },
    Kumlinge: { },
    Sottunga: { },
    Kökar: { name_fi_in: "Kökarissa"},
    Brändö: { },
    Iniö: { },
    Houtskär: { name_fi: "Houtskari"},
    Korpo: { name_fi: "Korppoo"},
    Nagu: { name_fi: "Nauvo"},
    Pargas: { name_fi: "Parainen", name_fi_in: "Paraisilla"},
    Kaarina: { name_sv: "S:t Karins"},
    Turku: { name_sv: "Åbo", name_fi_in: "Turussa"},
    Raisio: { name_sv: "Reso"},
    Naantali: { name_sv: "Nådendal"},
    Rymättylä: { name_sv: "Rimito"},
    Merimasku: { },
    Askainen: { name_sv: "Villnäs", name_fi_in: "Askaisissa"},
    Mietoinen: { name_fi_in: "Mietoisissa"},
    Velkua: {  name_fi_in: "Velkualla"},
    Taivassalo: { name_sv: "Tövsala" },
    Kustavi: { name_sv: "Gustavs" },
    Salo: { },
    Kimitoön: { name_fi: "Kemiönsaari", name_fi_in: "Kemiönsaaressa" },
    Hitis: { name_fi: "Hiittinen", name_fi_in: "Hiittisissä" },
    Norrskata: { },
    Houtsala: { },
    Hanko: { name_sv: "Hangö", name_fi_in: "Hangossa" },
  },

  ferries: {
    skiftet: {
      name: "M/S Skiftet",
      features: { access: true, cafe: true },
      capacity: { persons: 200, cars: 24, trucks: 4 },
      contact: {
        phones: [ '+358 (0)400 350 265', {name: 'Café', tel: '+358 (0)405 515 645'}]
      },
    },
    gudingen: {
      name: "M/S Gudingen",
      features: { access: true, cafe: true },
      capacity: { persons: 195, cars: 23, trucks: 4 },
      contact: {
        phones: [ '+358 (0)40 769 3687', {name: 'Café', tel: '+358 (0)405 505 059'}]
      },
    },
    ejdern: {
      name: "M/S Ejdern",
      features: { access: false, cafe: false },
      capacity: { persons: 99, cars: 16, trucks: 4 },
      contact: {
        phones: ['+358 (0)40 0229 260']
      },
    },
    skarven: {
      name: "M/S Skarven",
      features: { access: true, cafe: true },
      capacity: { persons: 250, cars: 65, trucks: 4 },
      contact: {
        phones: ['+358 (0)40 173 3600',{name: 'Café', tel: '+358 (0)457 3439 301'}]
      },
    },
    alfageln: {
      name: "M/S Alfågeln",
      features: { access: true, cafe: true },
      capacity: { persons: 244, cars: 38, trucks: 4 },
      contact: {
        phones: ['+358 (0)40 768 2108',{name: 'Café', tel: '+358 (0)40 637 8500'}]
      },
    },
    knipan: {
      name: "M/S Knipan",
      features: { access: true, cafe: false },
      capacity: { persons: 157, cars: 22, trucks: 4 },
      contact: {
        phones: ['+358 (0)40 0229 261']
      },
    },
    viggen: {
      name: "M/S Viggen",
      features: { access: true, cafe: true },
      capacity: { persons: 250, cars: 38, trucks: 4 },
      contact: {
        phones: ['+358 (0)40 0330 455', {name: 'Café', tel: '+358 (0)40 7658 453'}]
      },
    },
    adan: {
      name: "M/S Ådan",
      features: { access: true, cafe: true },
      capacity: { persons: 145, cars: 42, trucks: 4 },
      contact: {
        phones: ['+358 (0)40 4879 205']
      },
    },
    doppingen: {
      name: "M/S Doppingen",
      features: { access: false, cafe: false },
      capacity: { persons: 70, cars: 12, trucks: 2 },
      contact: {
        phones: ['+358 (0)40 7082 136']
      },
    },
    rosala: {
      name: "M/S Bärö",
      features: { access: false, cafe: false },
      capacity: { persons: 65, cars: 6, trucks: 1 },
      contact: {
        phones: ['+358 (0)40 0492 739']
      },
    },
    tuuli: {
      name: "M/S Tuuli",
      features: { access: false, cafe: false },
      capacity: { persons: 60, cars: 14, trucks: 2 },
      contact: {
        phones: ['+358 (0)40 0492 739']
      },
    },
    frida: {
      name: "M/S Frida II",
      features: { access: false, cafe: false },
      capacity: { persons: 70, cars: 18, trucks: 2 },
      contact: {
        phones: ['+358 (0)457 3613 394']
      },
    },
    odin: {
      name: "M/S Odin",
      features: { access: true, cafe: false },
      capacity: { persons: 99, cars: 41, trucks: 3 },
      contact: {
        phones: ['+358 (0)40 4840 352']
      },
    },
    angosundslinjen: {
      name: "Ängösundslinjes färja",
      features: { },
      capacity: { cars: 14 },
      contact: {
        phones: ['+358 457 529 5082']
      },
    },
    toftolinjen: {
      name: "Töftölinjes färja",
      features: { },
      capacity: { cars: 14 },
      contact: {
        phones: ['+358 457 342 1279']
      },
    },
    bjorkolinjen: {
      name: "Björkölinjes färja",
      features: { },
      capacity: { cars: 14 },
      contact: {
        phones: ['+358 457 524 2854']
      },
    },
    simskalalinjen: {
      name: "Simskälälinjes färja",
      features: { },
      capacity: { cars: 14 },
      contact: {
        phones: ['+358 457 379 8869']
      },
    },
    embarsundslinjen: {
      name: "Embarsundslinjes färja",
      features: { },
      capacity: { cars: 14 },
      contact: {
        phones: ['+358 457 379 8871']
      },
    },
    seglingelinjen: {
      name: "Seglingelinjes färja",
      features: { },
      capacity: { cars: 14 },
      contact: {
        phones: ['+358 40 768 5792']
      },
    },



    hammaronsalmi: {
      name: "Lautta #185",
      features: { },
      capacity: { cars: 14 },
      contact: {
        phones: ['+358 40 558 2773']
      },
    },
    hogsar: {
      name: "Lautta #182",
      features: { },
      capacity: { cars: 10 },
      contact: {
        phones: ['+358 40 558 4412']
      },
    },
    hogsara: {
      name: "Lautta #151",
      features: { },
      capacity: { cars: 14 },
      contact: {
        phones: ['+358 40 706 6291']
      },
    },
    aura: {
      name: "M/S Aura",
      features: { },
      capacity: { cars: 52,
        persons: 197,
      },
      contact: {
        phones: ['+358 400 320 093']
      },
    },
    aurora: {
      name: "M/S Aurora",
      features: { },
      capacity: { cars: 52,
        persons: 197,
      },
      contact: {
        phones: ['+358 400 320 092']
      },
    },
    keistio: {
      name: "Lautta #177",
      features: { },
      capacity: { cars: 10 },
      contact: {
        phones: ['+358 40 846 9500']
      },
    },
    kivimolossi: {
      name: "Lautta #167",
      features: { },
      capacity: { cars: 14 },
      contact: {
        phones: ['+358 400 292 691']
      },
    },
    kokkila: {
      name: "Lautta #199",
      features: { },
      capacity: { cars: 21 },
      contact: {
        phones: ['+358 40 568 4911']
      },
    },
    stellakorppoo: {
      name: "M/S Stella",
      features: { cafe: false },
      capacity: { cars: 65 },
      contact: {
        // phones: ['+358 400 114 291', { name: "Café Stella", tel: "+358 400 611 994"}],
        // fb: { name: "Café Stella", uri: "https://www.facebook.com/cafestellakorpo" },
        phones: ['+358 400 114 291'],
      },
    },
    mergus: {
      name: "M/S Mergus",
      features: { },
      capacity: { cars: 27 },
      contact: {
        phones: ['+358 400 533 461']
      },
    },
    mossala: {
      name: "Lautta #176",
      features: { },
      capacity: { cars: 14 },
      contact: {
        phones: ['+358 40 553 1534']
      },
    },
    l317: {
      name: "Lautta #317",
      features: { },
      capacity: { cars: 52, persons: 200 },
      contact: {
        phones: ['+358 40 865 0602']
      },
    },
    prostvik1: {
      name: "M/S Prostvik 1",
      features: { },
      capacity: { cars: 30 },
      contact: {
        phones: ['+358 400 864 268']
      },
    },
    nagu2: {
      name: "M/S Nagu 2",
      features: { },
      capacity: { cars: 16 },
      contact: {
        phones: ['+358 400 882 614']
      },
    },
    falko: {
      name: "M/S Falkö",
      features: { },
      capacity: { cars: 8,
        persons: 110,
      },
      contact: {
        phones: ['+358 400 320 097']
      },
    },
    kokkomaa: {
      name: "M/S Kokkomaa",
      features: { cafe: false },
      capacity: { cars: 8,
        persons: 99
      },
      contact: {
        phones: ['+358 50 400 1941']
      },
    },
    palva: {
      name: "Lautta #179",
      features: { },
      capacity: { cars: 10 },
      contact: {
        phones: ['+358 400 525 901']
      },
    },
    elektra: {
      name: "M/S Elektra",
      features: { },
      capacity: { cars: 90,
        persons: 450,
      },
      contact: {
        phones: ['+358 40 662 1320']
      },
    },
    altera: {
      name: "M/S Altera",
      features: { },
      capacity: { cars: 90,
        persons: 450,
      },
      contact: {
        phones: ['+358 40 565 4899']
      },
    },
    sterna: {
      name: "M/S Sterna",
      features: { },
      capacity: { cars: 66 },
      contact: {
        phones: ['+358 400 110 114']
      },
    },
    falco: {
      name: "M/S Falco",
      features: { },
      capacity: { cars: 54 },
      contact: {
        phones: ['+358 400 533 461']
      },
    },
    viken: {
      name: "M/S Viken",
      features: { },
      capacity: { cars: 14,
        persons: 73,
      },
      contact: {
        phones: ['+358 400 320 099']
      },
    },
    antonia: {
      name: "M/S Antonia",
      features: { cafe: true },
      capacity: { cars: 27 },
      contact: {
        phones: ['+358 40 738 3002']
      },
    },
    saverkeit: {
      name: "Lautta #181",
      features: { },
      capacity: { cars: 10 },
      contact: {
        phones: ['+358 40 553 1072']
      },
    },
    vartsala: {
      name: "Lautta #198",
      features: { },
      capacity: { cars: 36 },
      contact: {
        phones: ['+358 400 138 239']
      },
    },
    velkuanmaa: {
      name: "Lautta #171",
      features: { },
      capacity: { cars: 10 },
      contact: {
        phones: ['+358 400 525 902']
      },
    },
    mskivimo: {
      name: "M/S Kivimo",
      features: { },
      capacity: { cars: 8,
        persons: 50,
      },
      contact: {
        phones: ['+358 400 320 094']
      },
    },
    msfinno: {
      name: "M/S Finnö",
      features: { },
      capacity: { cars: " ", bikes: " ",
        persons: 50,
      },
      contact: {
        phones: ['+358  400 720 607']
      },
    },
    mskaita: {
      name: "M/S Kaita",
      features: { },
      capacity: { cars: 8,
        persons: 50,
      },
      contact: {
        phones: ['+358 400 320 095']
      },
    },
    msinnamo: {
      name: "M/S Innamo",
      features: { },
      capacity: { cars: 8,
        persons: 99,
      },
      contact: {
        phones: ['+358 40 861 0821']
      },
    },
    vano: {
      name: "Lautta #201",
      features: { },
      capacity: { cars: 21 },
      contact: {
        phones: ['+358 500 827 157']
      },
    },
    skagen: {
      name: "Vikare",
      features: { },
      capacity: { cars: 10 },
      contact: {
        phones: ['+358 50 379 1448'],
        email: 'vikare.ksloy@outlook.com',
      },
    },
    sorpo: {
      name: "Sorpo",
      features: { },
      capacity: { cars: 10 },
      contact: {
        phones: ['+358 40 569 2620']
      },
    },
    pettu: {
      name: "Pettu",
      features: { },
      capacity: { cars: 10 },
      contact: {
        phones: ['+358 50 354 2488'],
        email: "petunlossi@gmail.com",
      },
    },
    satava: {
      name: "M/S Satava",
      features: { },
      capacity: { cars: 8,
        persons: 80,
      },
      contact: {
        phones: ['+358 40 849 5140'],
        email: "satava@ferentes.fi"
      },
    },
    nordep: {
      name: "M/S Nordep",
      features: { cafe: true },
      capacity: { //cars: 2,
        persons: 78,
        bikes: " ",
      },
      contact: {
        phones: ['+358 45 129 4779'],
        fb: {name: "Salon risteilyt", uri: 'https://www.facebook.com/salonristeilyt'},
      },
    },
    karolina: {
      name: "M/S Karolina",
      features: { },
      capacity: { persons: 30, bikes: " " },
      contact: {
        phones: ['+358 40 717 3455 '],
      },
    },
    cheri: {
      name: "M/S Cheri",
      features: { },
      capacity: { persons: 12 },
      contact: {
        phones: ['+358 400 217 053', '+358 400 227 722']
      },
    },
    myrskylintu: {
      name: "M/S Myrskylintu",
      features: { },
      capacity: { persons: 28 },
      contact: {
        phones: ['+358 400 217 053', '+358 400 227 722']
      },
    },
    fisko: {
      name: "Y/A Fiskö",
      features: { },
      capacity: { cars: 2,
        persons: 36,
      },
      contact: {
        phones: ['+358 44 761 8000'],
        email: 'info@saaristolinjat.fi',
        email_sv: 'info@skargardslinjer.fi',
        fb: 'https://www.facebook.com/yaFisko/',
      },
    },
    isla: {
      name: "M/S Isla",
      features: { },
      capacity: { cars: 8,
        persons: 100,
      },
      contact: {
        phones: ['+358 40 673 6697'],
        fb: 'https://www.facebook.com/MS-Isla-401567819993437/'
      },
    },
    stellahiittinen: {
      name: "M/S Stella",
      features: { },
      capacity: { cars: 8,
        persons: 100,
      },
      contact: {
        phones: ['+358 40 675 6441'],
        fb: 'https://www.facebook.com/MS-Stella-1408172536122848/'
      },
    },
    alva: {
      name: "M/S Alva",
      features: { },
      capacity: { persons: 20 },
      contact: {
        phones: ['+358 40 413 1574']
      },
    },
    baldur: {
      name: "M/S Baldur",
      features: { cafe: true },
      capacity: { cars: 19,
        persons: 195
      },
      contact: {
        phones: ['+358 44 5000 503', {name: 'Café', tel: '+358 44 5000 506'}],
        fb: 'https://www.facebook.com/msbaldur'
      }
    },
    kokar: {
      name: "M/S Kökar",
      features: { cafe: true },
      capacity: { cars: 6,
        persons: 150
      },
      contact: {
        phones: ['+358 400 290 561', {name: 'Café', tel: '+358 400 290 541'}]
      }
    },
    ostern: {
      name: "M/S Östern",
      features: { cafe: true },
      capacity: { cars: 17,
        persons: 126
      },
      contact: {
        phones: ['+358 400 720 606'],
        email: 'info@ostern.fi',
        fb: 'https://www.facebook.com/YhteysalusOstern'
      }
    },
    aalto: {
      name: "M/S Aalto",
      features: { cafe: false },
      capacity: { cars: 6,
        persons: 70
      },
      contact: {
        phones: ['+358 400 720 606'],
        email: 'info@ostern.fi',
      }
    },
    silvana: {
      name: "M/S Silvana",
      features: { },
      capacity: { bikes: 50, persons: 50 },
      contact: {
        phones: ['+358 400 229149']
      }
    },
    norrskar: {
      name: "M/S Norrskär",
      features: { cafe: true },
      capacity: { persons: 98, bikes: " " },
      contact: {
      }
    },
    vidskar: {
      name: "M/S Vidskär",
      features: { cafe: true },
      capacity: { persons: 99, cars: 10, bikes: 20 },
      contact: {
      }
    },
    hamnskar: {
      name: "M/S Hamnskär",
      features: { cafe: true },
      capacity: { persons: 55, bikes: " " },
      contact: {
      }
    },
    utoexpress: {
      name: "M/S Utö Express",
      features: {  },
      capacity: { persons: 55 },
      contact: {
        phones: ["+358 45 124 5551"],
        fb: "https://www.facebook.com/profile.php?id=100069822060431"
      }
    },
    summersea: {
      name: "M/S Summersea",
      features: { cafe: true },
      capacity: { persons: 155, bikes: " " },
      contact: {
      }
    },
    cardinalII: {
      name: "M/S Cardinal II",
      features: { },
      capacity: { persons: 30, bikes: " " },
      contact: {
      }
    },
    // falken: {
    //   name: "M/S Falken",
    //   features: { },
    //   capacity: { persons: 24, bikes: " " },
    //   contact: {
    //   }
    // },
    sissel: {
      name: "M/S Sissel",
      features: { },
      capacity: { persons: 80, bikes: " " },
      contact: {
      }
    },
    idun: {
      name: "M/S Idun",
      features: { },
      capacity: { persons: 130, bikes: " " },
      contact: {
      }      
    },
    minandra: {
      name: "M/S Minandra",
      features: { },
      capacity: { persons: 40 },
      contact: {
      }
    },
    fanny: {
      name: "M/S Fanny",
      features: { cafe: true },
      capacity: { persons: 98, bikes: " " },
      contact: {
      }
    },
    aavatar: {
      name: "M/S Aavatar",
      features: { cafe: true },
      capacity: { persons: 52, bikes: " " },
      contact: {
        phones: ['+358 400 468 567']
      }
    },
    amanda: {
      name: "M/S Amanda",
      features: { cafe: true },
      capacity: { persons: 34, bikes: " " },
      contact: {
        phones: ['+358 400 669865']
      }
    },
  },

  operators: {
    alandstrafiken: {
      name: "Ålandstrafiken",
      logo: "alandstrafiken.png",
      contact: {
        phones: ['+358-18-25 600'],
        fax: '+358-18-17815',
        address: 'Styrmansgatan 1, AX-22100 MARIEHAMN',
        fb: 'https://www.facebook.com/%C3%85landstrafiken-trafikinformation-159908027409016/',
        email: 'info@alandstrafiken.ax',
        www: 'http://www.alandstrafiken.ax/',
      },
    },
    skarpnato: {
      name: "Skarpnåtö Turistanläggning",
      contact: {
        phones: ['+358 (0)18-37227'],
        email: 'britta.h@aland.net',
        www_fi: 'https://www.aland.com/p/skarpnato-turistanlaggning-suomeksi',
        www_sv: 'https://www.aland.com/p/skarpnato-turistanlaggning',
        www_en: 'https://www.aland.com/p/skarpnato-turistanlaggning-english',
      },
    },
    finferries: {
      name: "Finferries",
      logo: "finferries.png",
      contact: {
        phones: ['+358 207 118 750', {name: "Timetables", name_fi: "Aikatauluneuvonta", name_sv: "Tidtabellsinformation", tel: '+358 400 117 123'}],
        address: 'Puutarhakatu 55-57, PL 252, 20101 Turku',
        www: 'https://www.finferries.fi/',
        www_fi: 'https://www.finferries.fi/',
        www_sv: 'https://www.finferries.fi/sv',
        www_en: 'https://www.finferries.fi/en'
      },
    },
    ncl: {
      name: "Nordic Coast Line / Nordic Jetline",
      logo: "ncl.png",
      contact: {
        address: 'Mannerheiminkatu 20, 06100 Porvoo',
        phones: ['+358 19 536 2200'],
        fax: '+358 19 536 2201',
        email: 'info@nordiccoastline.fi',
        www: 'http://www.ncl.fi/fi',
        www_fi: 'http://www.ncl.fi/fi',
        www_sv: 'http://www.ncl.fi/sv',
        www_en: 'http://www.ncl.fi/en'
      },
    },
    kymensaaristoliikenne: {
      name: "Kymen Saaristoliikenne Oy",
      logo: "",
      contact: {
        address: 'Norpantie 15, 48310 Kotka',
        phones: ['+358 400 947 703'],

      }
    },
    ferryway: {
      name: "JS Ferryway Ltd Oy",
      logo: "ferryway.png",
      contact: {
        phones: [],
        email: 'info@ferryway.fi',
        address: 'Äpplö, 21760 Houtskari',
        www: 'https://www.ferryway.fi/'
      },
    },
    ferentes: {
      name: "Ferentes Oy",
      logo: "ferentes.png",
      contact: {
        phones: [],
        email: 'info@ferentes.fi',
        www: 'https://www.ferentes.fi/'
      },
    },
    al: {
      name: "Archipelago Lines",
      logo: "archipelagolines.png",
      contact: {
        phones: ['+358 41 456 4828', '+358 45 124 5551'],
        email: 'info@a-lines.fi',
        www: 'https://saaristolinjat.fi/',
        www_fi: 'https://saaristolinjat.fi/',
        www_sv: 'https://saaristolinjat.fi/?lang=sv'
      },
    },
    savolainen: {
      name: "Kuljetus Savolainen Oy",
      logo: 'kuljetussavolainen.png',
      contact: {
        phones: ['+358 6 533 0542', '+358 400 849444'],
        fax: '+358 6 5350500',
        email: 'info@kuljetus-savolainen.fi',
        www: 'https://kuljetus-savolainen.fi/yhteysalusliikenne/'
      },
    },
    sinv: {
      name: "Sundqvist Investment Oy",
      logo: "sinv.png",
      contact: {
        phones: [{name: "CEO", tel: '+358 442 510 297'}],
        email: 'mats.sundqvist@sinv.eu',
        www: 'https://www.ostern.fi/en/',
        www_fi: 'https://www.ostern.fi/',
        www_sv: 'https://www.ostern.fi/sv/',
      },
    },
    rosita: {
      name: "Rosita Oy",
      logo: "rosita.png",
      contact: {
        phones: ['+358 2 213 1500'],
        email: 'info@rosita.fi',
        address: 'Formaalintie 10, 20780 Kaarina',
        www: 'http://www.rosita.fi/',
        www_fi: 'http://www.rosita.fi/',
        www_sv: 'http://www.rosita.fi/Hemsida'
      },
    },
    meritie: {
      name: "Saariston Meritie Oy",
      logo: "meritie.png",
      contact: {
        phones: ['+358 45 124 5551'],
        address: 'Pansiontie 48, 20240 Turku',
        address_sv: 'Pansiovägen 48, 20240 Åbo',
        www: 'https://www.meritie.fi/',
        www_fi: 'https://www.meritie.fi/',
        www_sv: 'https://meritie.fi/?lang=sv',
        fb: 'https://www.facebook.com/Archipelagoway/'
      },
    },
    coastline: {
      name: "Coast Line",
      logo: "coastline_logo.png",
      contact: {
        phones: ['+358 50 400 1941'],
        email: 'coastline@eurowork.info',
        address: 'Pörtö, 01180 KALKKIRANTA',
        www: 'https://www.coast-line.fi/sv/',
        www_fi: 'https://www.coast-line.fi/',
        www_sv: 'https://www.coast-line.fi/sv/',
      },
    },
    vitharun: {
      name: "Vitharun",
      logo: "vitharun.png",
      contact: {
        phones: ['+358 400 176 684'],
        email: 'sales@vitharun.fi',
        fb: 'https://www.facebook.com/rederiabvitharun',
        www: 'https://vitharun.fi/fi/',
        www_sv: 'https://vitharun.fi/sv/',
        www_en: 'https://vitharun.fi/en/',
      }
    },
    airistonvesibussit: {
      name: "Airiston Vesibussit Oy",
      logo: "aavatar.png",
      contact: {
        phones: [{name: 'Turku Touring', tel:'+358 2 262 7444'}, {name: 'Visit Naantali', tel:'+358 2 435 9800'}],
        email: 'myynti@vesibussiaavatar.fi',
        www: 'http://www.vesibussiaavatar.fi/',
        www_sv: 'http://www.vesibussiaavatar.fi/sv/',
        www_en: 'http://www.vesibussiaavatar.fi/en/',
        fb: 'https://www.facebook.com/vesibussiaavatar/'
      }
    },
    aspocharter: {
      name: "Aspö Charter",
      logo: "aspocharter.png",
      contact: {
        phones: [{name: "Tore Johansson", tel: "+358 400 669865"}, {name: "Suomen Saaristovaraus", tel: "+358 2 410 6600"}],
        email: 'tore@aspocharter.com',
        www: 'https://sites.google.com/aspocharter.com/home',
        www_sv: 'https://sites.google.com/aspocharter.com/sve',
        www_en: 'https://sites.google.com/aspocharter.com/eng',
        fb: 'https://www.facebook.com/aspocharter/',
      }
    },
    wilsoncharter: {
      name: "Wilson Charter",
      logo: "wilsoncharter.png",
      contact: {
        phones: [{name: "Virpi Heino", tel: "+358 50 5514 266"}, {name: "Daniel Wilson", tel: "+358 50 5636 575"}],
        email: 'info@wilsoncharter.fi',
        www: 'https://www.wilsoncharter.fi/',
        www_sv: 'https://www.wilsoncharter.fi/se',
        www_en: 'https://www.wilsoncharter.fi/en',
        address: 'Båtmansvägen 18, 25950 Rosala',
        fb: "https://www.facebook.com/wilsoncharterFI/"
      }
    },
    // hankolines: {
    //   name: "Hanko Lines",
    //   logo: "hankolines.png",
    //   contact: {
    //     phones: ["+358 500 102 111"],
    //     email: 'info@hankolines.fi',
    //     www: 'http://www.hankolines.fi/',
    //   }
    // },
    marinelines: {
      name: "Marine Lines",
      logo: "marinelines.png",
      contact: {
        phones: ["+358 400 536 930", "+358 400 689 387"],
        email: 'myynti@marinelines.fi',
        www: 'https://marinelines.fi/fi',
        address: 'Korkeavuorenkatu 10 B 11, 10900 HANKO',
      }
    }
  },

  piers: {
    Långnäs: { mun: "Lumparland", type: "1" },
    BerghamnE: { name: "Berghamn", mun: "Eckerö", type: "1" },
    Grisslehamn: { mun: "Sverige", type: "1" },
    Mariehamn: { name_fi: "Maarianhamina", mun: "Mariehamn", type: "1" },
    Kapellskär: { mun: "Sverige", type: "1" },
    StockholmVärtan: { name: "Stockholm Värtan", mun: "Sverige", type: "1" },
    StockholmStadsgården: { name: "Stockholm Stadsgården", mun: "Sverige", type: "1" },
    Turku: { name_sv: "Åbo", mun: "Mariehamn", type: "1" },
    Naantali: { name_sv: "Nådendal", mun: "Naantali", type: "1" },
    Helsinki: { name_sv: "Helsingfors", mun: "Helsinki", type: "1" },
    Tallinn: { name_fi: "Tallinna", mun: "Eesti", type: "1" },

    Svinö: { name: "Svinö", mun: "Lumparland", type: "1" },
    Degerby: { name: "Degerby", mun: "Föglö", type: "1" },
    Hummelvik: { mun: "Vårdö", type: "1" },
    Enklinge: { mun: "Kumlinge" },
    Kumlinge: { mun: "Kumlinge", type: "1" },
    Lappo: { mun: "Brändö" },
    Torsholma: { mun: "Brändö", type: "1" },
    Asterholma: { mun: "Brändö" },
    Åva: { mun: "Brändö", type: "1" },
    JurmoB: { name: "Jurmo", mun: "Brändö" },
    Vuosnainen: {  name_sv: "Osnäs", mun: "Kustavi", type: "1" },
    Långnäs: { mun: "Lumparland", type: "1" },
    Överö: { mun: "Föglö", type: "1" },
    Sottunga: { mun: "Sottunga", type: "1" },
    Husö: { mun: "Sottunga" },
    Kyrkogårdsö: { mun: "Kökar" },
    Kökar: { mun: "Kökar" },
    Galtby: { mun: "Korpo", type: "1" }, 
    Bergö: { mun: "Vårdö" },
    Snäckö: { mun: "Kumlinge", type: "1" }, 
    Kannvik: { mun: "Iniö", type: "1" }, 
    Heponiemi: { mun: "Kustavi", type: "1" },
    Dalen: { mun: "Iniö", type: "1" },
    Mossala: { mun: "Houtskär", type: "1" }, 
    Kittuis: { mun: "Houtskär", type: "1" }, 
    Olofsnäs: { mun: "Norrskata", type: "1" }, 
    Retais: { mun: "Korpo", type: "1" }, 
    Pärnäs: { name_fi: "Pärnäinen", mun: "Nagu", type: "1" }, 
    Nagu: { name_fi: "Nauvo", mun: "Nagu", type: "1" }, 
    Hanka: { mun: "Rymättylä", type: "1" }, 
    Teersalo: { mun: "Velkua", type: "1" }, 
    Hakkenpää: { mun: "Taivassalo", type: "1" }, 
    Kasnäs: { mun: "Kimitoön", type: "1" }, 
    LångnäsH: { name: "Långnäs", mun: "Hitis", type: "1" }, 
    Haapala: { mun: "Rymättylä", type: "1" }, 
    Verkan: { mun: "Korpo", type: "1" }, 
    Kirjais: { name_fi: "Kirjainen", mun: "Nagu", type: "1" }, 
    Granvik: { mun: "Pargas", type: "1" }, 
    Prostvik: { mun: "Nagu", type: "1" }, 
    Lillmälö: { mun: "Pargas", type: "1" },
    Dalsbruk: { name_fi: "Taalintehdas", mun: "Kimitoön", type: "1" }, 

    Rauhala: { mun: "Velkua" },
    Lailuoto: { mun: "Velkua" },
    Talosmeri: { mun: "Velkua" },
    Munninmaa: { mun: "Velkua" },
    Tammisluoto: { mun: "Velkua" },
    Liettinen: { mun: "Velkua" },
    Kettumaa: { mun: "Velkua" },
    Ruotsalainen: { mun: "Rymättylä" },
    Korvenmaa: { mun: "Rymättylä" },
    Pyytti: { mun: "Rymättylä" },
    Pakinainen: { mun: "Rymättylä" },
    Pähkinäinen: { mun: "Rymättylä" },
    Samsaari: { name_sv: "Samsor", mun: "Rymättylä" },
    Maisaari: { mun: "Rymättylä" },
    Korpoström: { mun: "Korpo", type: "1" },
    Finnö: { mun: "Korpo" },
    Käldersö: { mun: "Korpo" },
    Elvsö: { mun: "Korpo" },
    BerghamnK: { name: "Berghamn", mun: "Houtskär" },
    Luk: { mun: "Houtskär" },
    Lillpensor: { mun: "Korpo" },
    Storpensor: { mun: "Houtskär" },
    Havträsk: { mun: "Norrskata", type: "1" }, 
    Brunskär: { mun: "Korpo" },
    Österskär: { mun: "Korpo" },
    Kälö: { mun: "Korpo" },
    Näsby: { mun: "Houtskär", type: "1" },
    Roslax: { mun: "Houtskär", type: "1" },
    Sördö: { mun: "Houtskär" },
    Lempnäs: { mun: "Houtskär" },
    Äpplö: { mun: "Houtskär" },
    Bockholm: { mun: "Houtskär" },
    Södö: { mun: "Houtskär" },
    Nåtö: { mun: "Houtskär" },
    Härklot: { mun: "Houtskär" },
    Själö: { mun: "Houtskär" },
    Norrby: { mun: "Iniö", type: "1" },
    Ytterstö: { mun: "Iniö" },
    Lempmo: { mun: "Iniö" },
    Salmis: { mun: "Iniö" },
    Lammholm: { mun: "Iniö" },
    Kvarnholm: { mun: "Iniö" },
    Åselholm: { mun: "Iniö" },
    Perkala: { mun: "Iniö" },
    PerkalaP: { name: "Perkala P", mun: "Iniö" },
    Kolko: { mun: "Iniö" },
    TorsholmaI: { name: "Torsholma", mun: "Brändö", type: "1" },
    Berghamn: { mun: "Nagu" },
    Nötö: { mun: "Nagu" },
    Aspö: { mun: "Korpo" },
    Jurmo: { mun: "Korpo" },
    Utö: { mun: "Korpo" },
//    Keso: { name: "Keso varvet", name_fi: "Keson telakka", mun: "Nagu", type: "1" }, 
    Seili: { name: "Själö", name_fi: "Seili", mun: "Nagu" },
    Innamo: { mun: "Nagu" },
    Järvsor: { mun: "Korpo" },
    Maskinnamo: { mun: "Korpo" },
    Åvensor: { name_fi: "Ahvensaari", mun: "Korpo" },
    Lavarn: { mun: "Houtsala", type: "1" }, 
    Granholmen: { mun: "Pargas" },
    Heisala: { mun: "Pargas" },
    Björkholm: { mun: "Pargas" },
    Ramsholm: { mun: "Pargas" },
    Stenholm: { mun: "Nagu" },
    Aspholm: { mun: "Nagu" },
    ÖstraTallholm: { name: "Östra Tallholm", mun: "Nagu" },
    Kuggö: { mun: "Pargas" },
    PensarI: { name: "Pensar I", mun: "Nagu" },
    Krok: { mun: "Nagu"},
    Mattnäs: { mun: "Nagu"},
    Lånholm: { mun: "Nagu"},
    Fagerholm: { mun: "Nagu"},
    Killingholm: { mun: "Nagu"},
    Ängsö: { mun: "Nagu"},
    Tveskiftsholm: { mun: "Nagu"},
    Berghamn: { mun: "Nagu"},
    Hummelholm: { mun: "Nagu"},
    Rockelholm: { mun: "Nagu"},
    Ytterstholm: { mun: "Nagu"},
    Byskär: { mun: "Nagu"},
    Brännskär: { mun: "Nagu"},
    Grötö: { mun: "Nagu"},
    Stenskär: { mun: "Nagu"},
    Gullkrona: { mun: "Nagu"},
    PensarL: { name: "Pensar L", mun: "Nagu"},
    Peno: { mun: "Nagu"},
    Knivskär: { mun: "Nagu"},
    Kopparholm: { mun: "Nagu"},
    Träskholm: { mun: "Nagu"},
    Bodö: { mun: "Nagu"},
    Björkö: { mun: "Korpo"},
    Gloskär: { mun: "Nagu"},
    Trunsö: { mun: "Nagu"},
    Sandholm: { mun: "Nagu"},
    Lökholm: { mun: "Nagu"},
    Borstö: { mun: "Nagu"},
    Tunnhamn: { mun: "Kimitoön"},
    Vänö: { mun: "Kimitoön"},
    Holma: { mun: "Kimitoön"},
    Helsingholm: { mun: "Kimitoön"},
    Biskopsö: { mun: "Kimitoön"},
    Grönvik: { mun: "Kimitoön"},
    Ängesö: { name: "Stora Ängesö", mun: "Kimitoön"},
    Bolax: { mun: "Kimitoön"},
    Bötesö: { mun: "Kimitoön"},
    Djupö: { mun: "Kimitoön"},
    Örö: { mun: "Kimitoön"},
    ÖröP: { name: "Örö P", mun: "Kimitoön"},
    Rosala: { mun: "Kimitoön"},
    Vikare: { mun: "Kimitoön"},
    Söderlångvik: { mun: "Kimitoön"},
    Bengtskär: { mun: "Kimitoön"},
    Vänoxaby: { name: "Vänoxa by", mun: "Kimitoön"},
    Vänoxasläten: { name: "Vänoxa släten (Bergö)", mun: "Kimitoön"},

    Hanko: { name_sv: "Hangö", mun: "Hanko"},
    Svartnäs: { mun: "Kimitoön" },
    Högsåra: { mun: "Kimitoön" },
    Kivimaa: { mun: "Kustavi" },
    Vartsala: { mun: "Kustavi" },
    Våno: { mun: "Pargas" },
    Mielisholm: { mun: "Pargas" },
    Grännäs: { mun: "Nagu" },
    Ängholm: { mun: "Nagu" },

    PalvaL: { name: "Palva", mun: "Velkua" },
    PalvaI: { name: "Palva", mun: "Velkua" },
    Velkuanmaa: {mun: "Velkua"},
    Kivimo: { mun: "Houtskär" },
    BjörköH: { name: "Björkö", mun: "Houtskär" },
    MossalaE: { name: "Mossala", mun: "Houtskär" },
    NäsbyI: { name: "Näsby", mun: "Houtskär" },
    Saverkeit: { mun: "Houtskär" },
    Airismaa: { mun: "Rymättylä" },
    Aasla:  { mun: "Rymättylä" },
    Röölä:  { mun: "Rymättylä" },
    Kokkila:  { mun: "Salo" },
    Angelniemi:  { mun: "Salo" },
    Keistiö:  { mun: "Iniö" },
    Skagen:  { mun: "Iniö" },
    JumoE:  { name: "Jumo", mun: "Iniö" },
    Pargas:  { name_fi: "Parainen", mun: "Pargas" },
    Sorpo:  { mun: "Pargas" },
    Jermo:  { mun: "Pargas" },
    Ulkoluoto:  { name_sv: "Utö", mun: "Salo" },
    Pettu: { mun: "Salo" },

    Sandö: { mun: "Vårdö", type: "1" },
    Simskäla: { mun: "Vårdö" },
    Prästö: { mun: "Sund", type: "1" },
    Töftö: { mun: "Vårdö", type: "1" },
    Finholma: { mun: "Föglö" },
    Jyddö: { mun: "Föglö" },
    Ängö: { mun: "Lumparland" },
    Norrboda: { mun: "Lumparland", type: "1" },
    Seglinge: { mun: "Kumlinge" },
    LappoL: { name: "Lappo", mun: "Brändö", type: "1" },
    BjörköK: { name: "Björkö", mun: "Kumlinge", type: "1" },

    Skarpnåtö: { mun: "Hammarland", type: "1" },
    Hällö: { mun: "Geta", type: "1" },
    SnäcköGeta: { name: "Snäckö", mun: "Geta", type: "1" },
    
    TurkuVitharun: { name: "Aurajoki", name_sv: "Aura å", name_en: "Aurajoki River", mun: "Turku", type: "1" },

//    NaantaliVanhakaupunki: { name: "Naantalin vanhakaupunki", name_sv: "Nådendals gamla stan", name_en: "Naantali Old Town", mun: "Naantali" },
    NaantaliVanhakaupunki: { name: "Naantali", name_sv: "Nådendal", mun: "Naantali", type: "1" },
    Merimasku: { mun: "Merimasku", type: "1" },
    Parattula: { mun: "Kustavi", type: "1" },
    Kivimaa2: { name: "Kivimaa", mun: "Kustavi", type: "1" },
    Katanpää: { mun: "Kustavi" },

    Vuohensaari: { mun: "Salo" },
    Mathildedal: { mun: "Salo" },
  },

  timetables: {
    foglolinjen: {
      link: "https://www.alandstrafiken.ax/turlistor",
      tables: [
      { validFrom: "2023-01-01", validTo: "2023-05-31", images: ["foglo_28-29-1-0.jpg"]},
      { validFrom: "2023-06-01", validTo: "2023-08-31", images: ["foglo_28-29-1-1.jpg"]},
      { validFrom: "2023-09-01", validTo: "2023-12-31", images: ["foglo_28-29-1-0.jpg"]},
    ],
    },
    norralinjen: {
      specifier: "Hummelvik - Torsholma, M/S Alfågeln",
      link: "https://www.alandstrafiken.ax/turlistor",
      tables: [
      { validFrom: "2023-01-01", validTo: "2023-04-30", images: ["norra_hummelvik_30-35-1-0.jpg", "norra_hummelvik_30-35-1-1.jpg"]},
      { validFrom: "2023-05-01", validTo: "2023-06-08", images: ["norra_hummelvik_30-35-2-0.jpg", "norra_hummelvik_30-35-2-1.jpg"]},
      { validFrom: "2023-06-09", validTo: "2023-08-15", images: ["norra_hummelvik_30-35-3-0.jpg", "norra_hummelvik_30-35-3-1.jpg"]},
      { validFrom: "2023-08-16", validTo: "2023-10-01", images: ["norra_hummelvik_30-35-2-0.jpg", "norra_hummelvik_30-35-2-1.jpg"]},
      { validFrom: "2023-10-02", validTo: "2023-12-31", images: ["norra_hummelvik_30-35-1-0.jpg", "norra_hummelvik_30-35-1-1.jpg"]},
  ],
    },
    enklingelinjen: {
      specifier: "Enklinge - Kumlinge, M/S Tuuli",
      link: "https://www.alandstrafiken.ax/turlistor",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-06-08", images: ["enklinge-kumlinge_52-54-1-0.jpg", "enklinge-kumlinge_52-54-2-0.jpg"]},
        { validFrom: "2023-06-09", validTo: "2023-08-15", images: ["enklinge-kumlinge_52-54-1-1.jpg"]},
        { validFrom: "2023-08-16", validTo: "2023-12-31", images: ["enklinge-kumlinge_52-54-1-0.jpg", "enklinge-kumlinge_52-54-2-0.jpg"]},
      ],
    },
    brandokumlingelinjen: {
      specifier: "Enklinge - Torsholma, M/S Ejdern",
      link: "https://www.alandstrafiken.ax/turlistor",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-04-30", images: ["brando-kumlinge_40-45-1-0.jpg", "brando-kumlinge_40-45-1-1.jpg"]},
        { validFrom: "2023-05-01", validTo: "2023-06-08", images: ["brando-kumlinge_40-45-2-0.jpg", "brando-kumlinge_40-45-2-1.jpg"]},
        { validFrom: "2023-06-09", validTo: "2023-08-15", images: ["brando-kumlinge_40-45-3-0.jpg", "brando-kumlinge_40-45-3-1.jpg"]},
        { validFrom: "2023-08-16", validTo: "2023-10-01", images: ["brando-kumlinge_40-45-2-0.jpg", "brando-kumlinge_40-45-2-1.jpg"]},
        { validFrom: "2023-10-02", validTo: "2023-12-31", images: ["brando-kumlinge_40-45-1-0.jpg", "brando-kumlinge_40-45-1-1.jpg"]},
          ],
    },
    avajurmo: {
      link: "https://www.alandstrafiken.ax/turlistor",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-04-30", images: ["ava-jurmo_46-51-1-0.jpg", "ava-jurmo_46-51-1-1.jpg"]},
        { validFrom: "2023-05-01", validTo: "2023-06-08", images: ["ava-jurmo_46-51-2-0.jpg", "ava-jurmo_46-51-2-1.jpg"]},
        { validFrom: "2023-06-09", validTo: "2023-08-15", images: ["ava-jurmo_46-51-3-0.jpg", "ava-jurmo_46-51-3-1.jpg"]},
        { validFrom: "2023-08-16", validTo: "2023-10-01", images: ["ava-jurmo_46-51-2-0.jpg", "ava-jurmo_46-51-2-1.jpg"]},
        { validFrom: "2023-10-02", validTo: "2023-12-31", images: ["ava-jurmo_46-51-1-0.jpg", "ava-jurmo_46-51-1-1.jpg"]},
      ],
    },
    osnasava: {
      link: "https://www.alandstrafiken.ax/turlistor",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-04-30", images: ["norra_osnas_36-39-1-0.jpg", "norra_osnas_36-39-1-1.jpg"]},
        { validFrom: "2023-05-01", validTo: "2023-06-08", images: ["norra_osnas_36-39-2-0.jpg"]},
        { validFrom: "2023-06-09", validTo: "2023-08-15", images: ["norra_osnas_36-39-2-1.jpg"]},
        { validFrom: "2023-08-16", validTo: "2023-10-01", images: ["norra_osnas_36-39-2-0.jpg"]},
        { validFrom: "2023-10-02", validTo: "2023-12-31", images: ["norra_osnas_36-39-1-0.jpg", "norra_osnas_36-39-1-1.jpg"]},
      ],
    },
    sodralinjen: {
      link: "https://www.alandstrafiken.ax/turlistor",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-04-05", images: ["sodra_16-25-1-0.jpg", "sodra_16-25-1-1.jpg"]},
        { validFrom: "2023-04-06", validTo: "2023-04-10", images: ["sodra_16-25-5-0.jpg"]},
        { validFrom: "2023-04-11", validTo: "2023-04-30", images: ["sodra_16-25-1-0.jpg", "sodra_16-25-1-1.jpg"]},
        { validFrom: "2023-05-01", validTo: "2023-06-11", images: ["sodra_16-25-2-0.jpg", "sodra_16-25-2-1.jpg"]},
        { validFrom: "2023-06-12", validTo: "2023-06-21", images: ["sodra_16-25-3-0.jpg", "sodra_16-25-3-1.jpg", "sodra_16-25-4-0.jpg", "sodra_16-25-4-1.jpg"]},
        { validFrom: "2023-06-22", validTo: "2023-06-26", images: ["sodra_16-25-3-1.jpg", "sodra_16-25-4-1.jpg"]},
        { validFrom: "2023-06-27", validTo: "2023-08-15", images: ["sodra_16-25-3-0.jpg", "sodra_16-25-3-1.jpg", "sodra_16-25-4-0.jpg", "sodra_16-25-4-1.jpg"]},
        { validFrom: "2023-08-16", validTo: "2023-10-01", images: ["sodra_16-25-2-0.jpg", "sodra_16-25-2-1.jpg"]},
        { validFrom: "2023-10-02", validTo: "2023-12-23", images: ["sodra_16-25-1-0.jpg", "sodra_16-25-1-1.jpg"]},
        { validFrom: "2023-12-24", validTo: "2023-12-31", images: ["sodra_16-25-5-1.jpg"]},
      ],
    },
    tvarlinjen: {
      link: "https://www.alandstrafiken.ax/turlistor",
      tables: [
        { validFrom: "2022-01-01", validTo: "2022-04-24", images: ["Skargardsguiden_TURLISTOR_2022-12.jpg", "Skargardsguiden_TURLISTOR_2022-13.jpg"]},
        { validFrom: "2022-04-25", validTo: "2022-06-08", images: ["Skargardsguiden_TURLISTOR_2022-14.jpg", "Skargardsguiden_TURLISTOR_2022-15.jpg"]},
        { validFrom: "2022-06-09", validTo: "2022-08-15", images: ["Skargardsguiden_TURLISTOR_2022-16.jpg", "Skargardsguiden_TURLISTOR_2022-17.jpg"]},
        { validFrom: "2022-08-16", validTo: "2022-10-02", images: ["Skargardsguiden_TURLISTOR_2022-14.jpg", "Skargardsguiden_TURLISTOR_2022-15.jpg"]},
        { validFrom: "2022-10-03", validTo: "2022-12-31", images: ["Skargardsguiden_TURLISTOR_2022-12.jpg", "Skargardsguiden_TURLISTOR_2022-13.jpg"]},
        { validFrom: "2023-01-01", validTo: "2023-04-30", images: ["tvargaende_10-15-1-0.jpg", "tvargaende_10-15-1-1.jpg"]},
        { validFrom: "2023-05-01", validTo: "2023-06-08", images: ["tvargaende_10-15-2-0.jpg", "tvargaende_10-15-2-1.jpg"]},
        { validFrom: "2023-06-09", validTo: "2023-08-15", images: ["tvargaende_10-15-3-0.jpg", "tvargaende_10-15-3-1.jpg"]},
        { validFrom: "2023-08-16", validTo: "2023-10-01", images: ["tvargaende_10-15-2-0.jpg", "tvargaende_10-15-2-1.jpg"]},
        { validFrom: "2023-10-02", validTo: "2023-12-31", images: ["tvargaende_10-15-1-0.jpg", "tvargaende_10-15-1-1.jpg"]},
      ],  
    },
    alandsvajerfarjor: {
      link: "https://www.alandstrafiken.ax/turlistor",
      tables: [
      { validFrom: "2022-01-01", validTo: "2022-12-31", images: ["Skargardsguiden_TURLISTOR_2022-09.jpg"]},
      { validFrom: "2023-01-01", validTo: "2023-12-31", images: ["teckenforklaring_vajerfarjor_6-7-1-1.jpg"]},
    ],
    },
    seglingelinjen: {
      link: "https://www.alandstrafiken.ax/turlistor",
      tables: [
        { validFrom: "2022-01-01", validTo: null, images: ["Skargardsguiden_TURLISTOR_2022-9.jpg"]},
      ],
    },
    toftolinjen: {
      link: "https://www.alandstrafiken.ax/turlistor",
      tables: [
        { validFrom: "2023-01-01", validTo: null, images:["toftolinjens_turlista_2023_ny_senaste_2022.12.12-2-0.jpg", "toftolinjens_turlista_2023_ny_senaste_2022.12.12-2-1.jpg"] },
      ],
    },
    
    
    skarpnatosnacko: {
      link: "https://www.aland.com/p/skarpnato-turistanlaggning-suomeksi",
      link_sv: "https://www.aland.com/p/skarpnato-turistanlaggning",
      link_en: "https://www.aland.com/p/skarpnato-turistanlaggning-in-english",
      // tables_fi: [
      // { validFrom: "2018-06-20", validTo: "2018-08-20", images: ["Silvana2018_1.jpeg"]},
      // ],
      // tables_sv: [
      // { validFrom: "2018-06-20", validTo: "2018-08-20", images: ["Silvana2018_2.jpeg"]},
      // ],
      // tables_en: [
      // { validFrom: "2018-06-20", validTo: "2018-08-20", images: ["Silvana2018_3.jpeg"]},
      // ],

    },
    iniokustavi: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/inio-kustavi.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/inio-gustavs.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/inio-kustavi.html#timetables",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-05-11", images: ["inio-kustavi-sterna-1.1.-11.5.2023-1.jpg"]},
        { validFrom: "2023-05-12", validTo: "2023-09-03", images: ["inio-kustavi-kesaaikataulu-12.5.-3.9.2023.jpg"]},
        // { validFrom: "2023-09-04", validTo: "2023-12-31", images: ["inio-kustavi-sterna-1.1.-11.5.2023-1.jpg"]},
      ]
    },
    houtskarinio: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/saariston-rengastie-houtskari-inio.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/skargardens-ringvag-houtskar-inio.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/the-archipelago-houtskari-inio.html#timetables",
      tables: [
        { validFrom: "2021-05-14", validTo: "2021-08-29", images: ["aikataulu-2020-ja-2021-houtskari-inio-antonia-1.jpg"]},
        { validFrom: "2022-05-13", validTo: "2022-09-04", images: ["saariston-rengastie-houtskari-inio-antonia-13.5.-4.9.2022-1.jpg"]},
        { validFrom: "2023-05-12", validTo: "2023-09-03", images: ["saariston-rengastie-houtskari-inio-antonia-12.5.-3.9.2023.jpg"]},
      ],
    },

    korpohoutskar: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/korppoo-houtskari.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/korpo-houtskar.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/korppoo-houtskari.html#timetables",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-04-16", images: ["saaristotien-lautta-aikataulut-1.1.-16.4.2023-4.jpg"]},
      ],
    },
    korponorrskata: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/korppoo-norrskata.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/korpo-norrskata.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/korppoo-norrskata.html#timetables",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-04-16", images: ["saaristotien-lautta-aikataulut-1.1.-16.4.2023-4.jpg"]},
      ],
    },
    nagukorpo: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/nauvo-korppoo.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/nagu-korpo.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/nauvo-korppoo.html#timetables",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-04-16", images: ["saaristotien-lautta-aikataulut-1.1.-16.4.2023-3.jpg", "saaristotien-lautta-aikataulut-1.1.-16.4.2023-4b.jpg"]},
      ],
    },
    pargasnagu: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/parainen-nauvo.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/pargas-nagu.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/parainen-nauvo.html#timetables",        
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-04-16", images: ["saaristotien-lautta-aikataulut-1.1.-16.4.2023-2.jpg", "saaristotien-lautta-aikataulut-1.1.-16.4.2023-4b.jpg"]},
      ],
      },
    velkuataivassalo: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/velkuan-reitti-kaita.html",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/velkua-rutt-kaita.html",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/velkua-route-kaita.html",
      tables: [
        { validFrom: "2021-06-01", validTo: "2021-09-01", images: ["velkuan-reitti-01.06.-01.09.2021-1.jpg"]},
        { validFrom: "2022-05-18", validTo: "2022-09-15", images: ["velkua-kesa2022-fi-ja-se-1.jpg"]},
        { validFrom: "2023-05-12", validTo: "2023-09-03", images: ["velkuan-reitti-12.5.-3.9.2023.jpg"]},
      ],
    },

    nauvohanka: {
      name: "M/S Östern", specifier: "",
      link: "https://www.ostern.fi/aikataulut/",
      link_sv: "https://www.ostern.fi/sv/tidtabell/",
      link_en: "https://www.ostern.fi/en/schedule/",
      tables: [
      ],
    },
    nauvohankaturku: {
      name: "Yhdistelmä M/S Aalto & M/S Östern", name_sv: "Kombination M/S Aalto & M/S Östern", name_en: "Combined M/S Aalto & M/S Östern", specifier: "",
      link: "https://www.ostern.fi/b/ms-aalto-taydentaa-ms-osternin-kapasiteettia-pienella-rengastiella",
      tables: [
        { validFrom: "2020-07-21", validTo: "2020-08-16", images: ["Aaltoaikataulu_muokattu-1.jpg"]},
      ],
    },
    kasnashitis: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/kasnas-hiittinen.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/kasnas-hitis.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/kasnas-hiittinen.html#timetables",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-12-31", images: ["kasnas-hiittinen-aurora-1.1.-31.12.2023-1.jpg"]},
      ],
    },
    velkuanreitti: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/velkuan-reitti-kaita.html",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/velkua-rutt-kaita.html",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/velkua-route-kaita.html",
      tables: [
        { validFrom: "2022-09-16", validTo: "2023-05-11", images: ["velkuan-reitti-talvi-2022-2023-1.jpg"]},
        { validFrom: "2023-05-12", validTo: "2023-09-03", images: ["velkuan-reitti-12.5.-3.9.2023.jpg"]},
      ],
    },
    rymattylanreitti: {
      link: "https://meritie.fi/aikataulut/",
      link_sv: "https://meritie.fi/tidtabeller/?lang=sv",
      link_en: "https://meritie.fi/tidtabeller/?lang=sv",
      tables: [
        { validFrom: "2022-09-26", validTo: "2023-05-07", images:["Rymattyla-Syksy-2022-Talvi-Kevat-2023-1.jpg", "Rymattyla-Syksy-2022-Talvi-Kevat-2023-2.jpg"] },
        { validFrom: "2023-05-08", validTo: "2023-09-24", images:["Rymattyla-Ya-Isla-kesa-2023-1.jpg", "Rymattyla-Ya-Isla-kesa-2023-2.jpg"] },
      ],
    },
    houtskarrutt: {
      name: "Houtskarin reitti - M/S Finnö", name_sv: "Houtskär rutt - M/S Finnö", name_en: "Houtskär Route - M/S Finnö", specifier: "",
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/houtskarin-reitti-finno.html",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/houtskarsrutten-finno.html",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/houtskari-ruote-finno.html",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-05-31", images:["houtskarin-reitti-1.1.-31.5.2023-1.jpg", "houtskarin-reitti-1.1.-31.5.2023-2.jpg"] },
        { validFrom: "2023-06-01", validTo: "2023-06-08", images:["houtskarin-reitti-talvi-1.6-8.6.2023-ja-16.8.-31.5.2024-1.jpg", "houtskarin-reitti-talvi-1.6-8.6.2023-ja-16.8.-31.5.2024-2.jpg"] },
        { validFrom: "2023-06-09", validTo: "2023-08-15", images:["houtskarin-reitti-kesa-9.6.2023-15.8.2023-1.jpg", "houtskarin-reitti-kesa-9.6.2023-15.8.2023-2.jpg"] },
        { validFrom: "2023-08-16", validTo: "2024-05-31", images:["houtskarin-reitti-talvi-1.6-8.6.2023-ja-16.8.-31.5.2024-1.jpg", "houtskarin-reitti-talvi-1.6-8.6.2023-ja-16.8.-31.5.2024-2.jpg"] },
      ],
    },
    iniorutt: {
      name: "Iniön lisäreitti - M/S Kivimo", name_sv: "Iniö tilläggsrutt - M/S Kivimo", name_en: "Iniö Additional Route - M/S Kivimo", specifier: "",
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/inion-lisareitti-kivimo.html",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/inio-tillaggsrutt-kivimo.html",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/the-inio-additional-route-kivimo.html",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-05-31", images:["inion-lisareitti-1.1.-31.5.2023_1.9.-31.12.2023-1.jpg"] },
        { validFrom: "2023-06-01", validTo: "2023-08-31", images:["inion-lisareitti-kesa-1.6.2023-31.8.2023.jpg"] },
        { validFrom: "2023-09-01", validTo: "2023-12-31", images:["inion-lisareitti-1.1.-31.5.2023_1.9.-31.12.2023-1.jpg"] },
      ],
    },
    utorutt: { 
      link: "https://meritie.fi/aikataulut/",
      link_sv: "https://meritie.fi/tidtabeller/?lang=sv",
      link_en: "https://meritie.fi/tidtabeller/?lang=sv",
      tables: [
        { validFrom: "2022-09-01", validTo: "2023-06-04", images:["Baldur-talvi-2022-1-1.jpg"] },
        { validFrom: "2023-06-05", validTo: "2023-09-03", images:["Baldur-kesa-2023.jpg"] },
      ],
    },
    korporutt: {
      link: "https://saaristolinjat.fi/#reittialue",
      tables: [
        { validFrom: "2022-09-01", validTo: "2023-05-31", images:["Fisko-talviaikataulu-1.9.2022-31.5.2023-002-1.jpg"] },
        { validFrom: "2023-06-01", validTo: "2023-08-31", images:["Fisko-kesaaikataulu-2023.jpg"] },
      ],
    },
    nagunorra: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/nauvon-pohjoinen-reitti-innamo.html",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/nagu-norra-rutt-innamo.html",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/nauvo-northern-route-innamo.html",
      tables: [
        { validFrom: "2023-05-12", validTo: "2023-09-03", images:["nauvon-pohjoinen-reitti-12.5.-3.9.2023.jpg"] },
      ],
    },
    nagutvar: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/nauvon-poikittainen-reitti.html",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/nagu-tvargaende-rutt.html",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/nauvo-transverse-route.html",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-05-31", images:["nauvon-poikittainen-reitti-1.1.-31.5.2023-1.jpg"] },
        { validFrom: "2023-06-05", validTo: "2023-08-13", images:["nauvon-poikittainen-reitti-5.6.-13.8.2023.jpg"] },
      ],
    },
    nagusodra: { 
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/nauvon-etelainen-reitti-falko.html",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/nagu-sodra-rutt-falko.html",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/nauvo-southern-route-falko.html",
      tables: [
        { validFrom: "2023-01-01", validTo: "2023-04-30", images:["nauvon-etelainen-reitti-1.1.-31.5.2023-1.jpg"] },
        { validFrom: "2023-05-01", validTo: "2023-06-04", images:["nauvon-etelainen-reitti-1.5.-4.6.2023-ja-14.8.2023-2.6.2024.jpg"] },
        { validFrom: "2023-06-05", validTo: "2023-08-13", images:["nauvon-etelainen-reitti-5.6.-13.8.2023.jpg"] },
        { validFrom: "2023-08-14", validTo: "2024-06-02", images:["nauvon-etelainen-reitti-1.5.-4.6.2023-ja-14.8.2023-2.6.2024.jpg"] },
      ],
    },
    hitisstella: {
      name: "M/S Stella",
      link: "https://meritie.fi/aikataulut/",
      link_sv: "https://meritie.fi/tidtabeller/?lang=sv",
      link_en: "https://meritie.fi/tidtabeller/?lang=sv",
      tables: [
        { validFrom: "2022-08-15", validTo: "2023-06-03", images:["Hiittinen-Syksy-2022-Talvi-Kevat-2023-ei-pyhat-1.jpg", "Hiittinen-Syksy-2022-Talvi-Kevat-2023-ei-pyhat-2.jpg"] },
        { validFrom: "2023-06-04", validTo: "2023-08-13", images:["Ms-Stella-Kesa-2023-1.jpg", "Ms-Stella-Kesa-2023-2.jpg"] },
      ],
    },
    hitisalva: { 
      name: "M/S Alva",
      link: "https://meritie.fi/aikataulut/",
      link_sv: "https://meritie.fi/tidtabeller/?lang=sv",
      link_en: "https://meritie.fi/tidtabeller/?lang=sv",
      tables: [
        { validFrom: "2022-08-15", validTo: "2023-06-04", images:["Alva-syksy-22-1.jpg"]},
        { validFrom: "2023-06-05", validTo: "2023-08-13", images:["Alva-kesa-2023.jpg"]},
      ],
    },
    pargasrutt: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/paraisten-reittialue-viken.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/pargas-ruttomrade-viken.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/parainen-route-viken.html#timetables",
      tables: [
        { validFrom: "2022-09-01", validTo: "2023-05-31", images: ["viken-1.9.2022-31.5.2023-1.jpg"]},
        { validFrom: "2023-06-01", validTo: "2023-08-31", images: ["paraisten-reittialue-1.6.-31.8.2023.jpg"]},
      ]
    },

    hogsara: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/hogsara.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/hogsara.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/hogsara.html#timetables",
      tables: [
        { validFrom: "2017-01-01", validTo: null, images: ["Hogsara.jpeg"]}
      ]
    },
    vartsala: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/vartsala.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/vartsala.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/vartsala.html#timetables",
      tables: [
        { validFrom: "2017-01-01", validTo: null, images: ["Vartsala2020.jpeg"]}
      ]
    },
    vano: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/vano.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/vano.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/vano.html#timetables",
      tables: [
        { validFrom: "2017-01-01", validTo: null, images: ["Vano2018_1.jpeg", "Vano2018_2.jpeg", "Vano2018_3.jpeg"]}
      ]
    },
    hogsar: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/hogsar.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/hogsar.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/hogsar.html#timetables",
    },
    kokkila: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/kokkila.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/kokkila.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/kokkila.html#timetables",
    },
    hammaronsalmi: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/hammaronsalmi.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/hammaronsalmi.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/hammaronsalmi.html#timetables",
      tables: [
        { validFrom: "2018-01-01", validTo: null, images: ["Hammaronsalmi.jpg"]}
      ]
    },
    palva: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/palva.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/palva.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/palva.html#timetables",
      tables: [
        { validFrom: "2018-01-01", validTo: null, images: ["Palva.jpg"]}
      ]
    },
    velkuanmaa: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/velkuanmaa.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/velkuanmaa.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/velkuanmaa.html#timetables",
      tables: [
        { validFrom: "2018-01-01", validTo: null, images: ["Velkuanmaa.jpg"]}
      ]
    },
    kivimo: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/kivimo.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/kivimo.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/kivimo.html#timetables",
    },
    saverkeit: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/saverkeit.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/saverkeit.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/saverkeit.html#timetables",
    },
    mossala: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/mossala.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/mossala.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/mossala.html#timetables",
    },
    keistio: {
      link: "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/keistio.html#timetables",
      link_sv: "https://www.finferries.fi/sv/farjetrafik/farjplatserna-och-tidtabellerna/keistio.html#timetables",
      link_en: "https://www.finferries.fi/en/ferry-traffic/ferries-and-schedules/keistio.html#timetables",
    },
    skagen: {
      link: "http://www.ksloy.fi/fi/lauttaliikenne/",
      link_sv: "http://www.ksloy.fi/fi/sv/lauttaliikenne/",
      link_en: "http://www.ksloy.fi/fi/en/lauttaliikenne/",
      tables: [
        { validFrom: "2018-01-01", validTo: null, images: ["skagen_fi.jpg"], images_sv: ["skagen_sv.jpg"], images_en: ["skagen_en.jpg"]}
      ]
    },
    sorpo: {
      link: "http://lautta.net/db/aikataulut/sorpo/sorpo.php?lang=fi",
      link_sv: "http://lautta.net/db/aikataulut/sorpo/sorpo.php?lang=sv",
      link_en: "http://lautta.net/db/aikataulut/sorpo/sorpo.php?lang=en",
    },
    pettu: {
      link: "http://www.petunlossi.com/lossi.html",
    },
    hankokasnas: {
      link: "https://www.wilsoncharter.fi/hanko-kasnas-ja-kasnas-oro",
      link_sv: "https://www.wilsoncharter.fi/se/hango-kasnas-och-kasnas-oro",
      link_en: "https://www.wilsoncharter.fi/en/hanko-kasnas-and-kasnas-oro",
      tables: [
        { validFrom: "2019-06-30", validTo: "2019-08-11", images_fi: ["Kustrutten2019_fi.jpg"], images: ["Kustrutten2019_sv.jpg"]},
      ],
    },
    // hankokasnasuto: {
    //   link: "http://www.hankolines.fi",
    // },
    kasnasorowilson: {
      link: "https://www.wilsoncharter.fi/oron-linnake-ja-kansallispuisto",
      link_sv: "https://www.wilsoncharter.fi/se/oro-fort-och-nationalpark",
      link_en: "https://www.wilsoncharter.fi/en/oro-fortress-tours",
      name: "Wilson Charter",
      tables: [
        { validFrom: "2019-06-01 ", validTo: "2019-08-11", images_fi: ["SisselOro2019_fi.jpeg"], images: ["SisselOro2019_sv.jpeg"], images_en: ["SisselOro2019_en.jpeg"]},
      ],
    },
    kasnasbengtskar: {
      link: "https://www.wilsoncharter.fi/bengtskar",
      link_sv: "https://www.wilsoncharter.fi/se/bengtskar",
      link_en: "https://www.wilsoncharter.fi/en/bengtskar",
      tables: [
        { validFrom: "2018-06-01", validTo: "2018-08-25", images_fi: ["SisselBengtskar2018_fi.jpeg"], images_sv: ["SisselBengtskar2018_sv.jpeg"], images_en: ["SisselBengtskar2018_en.jpeg"]},
      ],
    },
    hankobengtskar: {
      link: "https://marinelines.fi/fi/risteilyt/bengtskar",
      tables: [
        { validFrom: "2018-06-19", validTo: "2018-08-25", images: ["Summersea2018.jpeg"]},
      ],
    },
    saaristolinja: {
      link: "https://vitharun.fi/fi/aikataulut/turku-seili-nauvo/",
      link_sv: "https://vitharun.fi/sv/tidtabeller/abo-sjalo-nagu/",
      link_en: "https://vitharun.fi/en/timetables/turku-seili-nagu/",
      tables: [
        { validFrom: "2020-05-01", validTo: "2020-09-27", images_fi: ["Norrskar2020_fi.jpeg"], images_sv: ["Norrskar2020_sv.jpeg"], images: ["Norrskar2020_en.jpeg"]},
      ],
    },
    utoexpress: {
      link: "https://www.utohotel.fi/uto-express/",
      tables: [
        { validFrom: "2022-06-22", validTo: "2022-08-12", images: ["Uto-Express-2022-ver-1.0-1.jpg"]},
      ],
    },
    naantalikustavi: {
      link: "https://www.visitnaantali.com/fi/saaristoreitti-kustaviin",
      link_en: "https://www.visitnaantali.com/en/archipelago-route-to-kustavi",
      // tables: [
      // { validFrom: "2018-07-07", validTo: "2018-08-04", images: ["Aavatar2018_fi.jpeg"], images_en: ["Aavatar2018_en.jpeg"]}
      // ],
    },
    korpostromoro: {
      link: "https://sites.google.com/aspocharter.com/home/reittiliikenne",
      link_sv: "https://sites.google.com/aspocharter.com/sve/utsk%C3%A4rs-tv%C3%A4rtrafik",
      link_en: "https://sites.google.com/aspocharter.com/eng/route-traffic",
      // tables: [
      // { validFrom: "2018-05-24", validTo: "2018-08-07", images: ["Amanda2018_1fi.jpeg", "Amanda2018_3fi.jpeg"], images_sv: ["Amanda2018_1sv.jpeg", "Amanda2018_3sv.jpeg"], images_en: ["Amanda2018_1en.jpeg", "Amanda2018_2en.jpeg", "Amanda2018_3en.jpeg"]}
      // ],
    }

  },

  pricelists: {
    alandstrafiken: [
      { validFrom: "2018-01-01", validTo: "2018-12-31", lists: ["AlandstrafikenPricelist2018_1.jpeg", "AlandstrafikenPricelist2018_2.jpeg"]}
    ]
  },

  routes: {
    foglolinjen: {
      name: "Föglölinjen",
      name_fi: "Föglön linja",
      name_en: "Föglo line",
      specifier: "Svinö - Degerby",
      piers: ["Svinö", "Degerby"],
      operator: "alandstrafiken",
      vessels: ["skarven"],
      features: {
        interval_L: ["times.aday", "8-12"],
        booking_L: "booking.cannot",
        cost_L: "cost.applies",
        duration_L: ["duration.minutes", "35"]
      },
      timetables: "foglolinjen",
      pricelists: "alandstrafiken"
    },
    norralinjen: {
      name: "Norra linjen",
      name_fi: "Pohjoinen linja",
      name_en: "Northern line",
      specifier: "Hummelvik - Torsholma",
      piers: ["Hummelvik", "Enklinge", "Kumlinge", "Asterholma", "Lappo", "Torsholma"],
      operator: "alandstrafiken",
      vessels: ["alfageln", "ejdern", "tuuli"],
      features: {
        interval_L: ["times.adaytworoutes", "", "2-4", "Enklinge - Kumlinge", "10"],
        cost_L: "cost.applies",
        duration_L: ["duration.hours", "2.5"],
      },
      timetables: ["norralinjen", "brandokumlingelinjen", "enklingelinjen"],
      pricelists: "alandstrafiken"
    },
    avajurmo: {
      name: "Norra linjen",
      name_fi: "Pohjoinen linja",
      name_en: "Northern line",
      specifier: "Åva - Jurmo",
      piers: ["Åva", "JurmoB"],
      operator: "alandstrafiken",
      vessels: ["doppingen"],
      features: {
        interval_L: ["times.aday", "10-15"],
        order_L: "order.partly",
        duration_L: ["duration.minutes", "10"]
      },
      timetables: "avajurmo",
      pricelists: "alandstrafiken"
    },
    osnasava: {
      name: "Norra linjen",
      name_fi: "Pohjoinen linja",
      name_en: "Northern line",
      specifier: "Vuosnainen - Åva",
      specifier_sv: "Osnäs - Åva",
      piers: ["Vuosnainen", "Åva"],
      operator: "alandstrafiken",
      vessels: ["adan"],
      features: {
        interval_L: ["times.aday", "3-4"],
        cost_L: "cost.applies",
        duration_L: ["duration.minutes", "40"]
      },
      timetables: "osnasava",
      pricelists: "alandstrafiken"
    },
    sodralinjen: {
      name: "Södra linjen",
      name_fi: "Eteläinen linja",
      name_en: "Southern line",
      specifier: "Långnäs - Överö - Sottunga - Kökar - Galtby",
      piers: ["Långnäs", "Överö", "Sottunga", "Husö", "Kyrkogårdsö", "Kökar", "Galtby"],
      operator: "alandstrafiken",
      vessels: ["gudingen", "viggen", "skiftet"],
      features: {
        interval_L: ["times.aday", "Långnäs - Kökar 3-4, Kökar - Galtby 0-2 "],
        cost_L: "cost.applies",
        duration: "Långnäs - Kökar 2.5&nbsp;hours, Kökar - Galtby 2.5&nbsp;hours",
        duration_fi: "Långnäs - Kökar 2,5&nbsp;tuntia, Kökar - Galtby 2,5&nbsp;tuntia",
        duration_sv: "Långnäs - Kökar 2,5&nbsp;timmar, Kökar - Galtby 2,5&nbsp;timmar",
      },
      timetables: "sodralinjen",
      pricelists: "alandstrafiken"
    },
    tvarlinjen: {
      name: "Tvärgående linjen",
      name_fi: "Poikittainen linja",
      name_en: "Cross line",
      specifier: "Långnäs - Överö - Sottunga - Snäckö",
      piers: ["Långnäs", "Bergö", "Överö", "Sottunga", "Snäckö" ],
      operator: "alandstrafiken",
      vessels: ["odin"],
      features: {
        interval_L: ["times.aday", "1-2"],
        cost_L: "cost.applies",
        duration_L: ["duration.hourminutes", "45"],
        order_L: ["order.pieronly", "Överö"],
      },
      notes: [
      { 
        content: "<div>Bergö and Sottunga are not served regularly</div>",
        content_fi: "<div>Bergössä ja Sottungassa poiketaan vain harvoin</div>",
        content_sv: "<div>Bergö och Sottunga trafikeras ovanligen</div>"
      }
      ],
      timetables: "tvarlinjen",
      pricelists: "alandstrafiken"
    },

    iniokustavi: {
      name: "Iniö - Kustavi",
      name_sv: "Iniö - Gustavs",
      specifier: "",
      piers: ["Kannvik", "Heponiemi"],
      operator: "finferries",
      vessels: ["aura"],
      features: {
        interval_L: ["times.aday", "5-8"],
        duration_L: ["duration.minutes", "25"],
      },
      timetables: "iniokustavi",
    },

    houtskarinio: {
      name: "Houtskär - Iniö",
      name_fi: "Houtskari - Iniö",
      specifier: "",
      piers: ["Mossala", "Dalen"],
      operator: "finferries",
      vessels: ["antonia"],
      features: {
        interval_L: ["times.aday", "3-4"],
        duration_L: ["duration.minutes", "50"],
        seasonal_L: "seasonal.summers",
        cost_L: "cost.applies",
      },
      timetables: "houtskarinio",
    },

    korpohoutskar: {
      name: "Korpo - Houtskär",
      name_fi: "Korppoo - Houtskari",
      specifier: "",
      piers: ["Galtby", "Kittuis"],
      operator: "finferries",
      vessels: ["stellakorppoo", "falco"],
      features: {
        interval_L: ["times.aday", "10-12"],
        order_L: "order.partly",
        duration_L: ["duration.minutes", "35"],
      },

      timetables: "korpohoutskar",
    },

    korponorrskata: {
      name: "Korpo - Norrskata",
      name_fi: "Korppoo - Norrskata",
      specifier: "",
      piers: ["Galtby", "Olofsnäs"],
      operator: "finferries",
      vessels: ["falco", "stellakorppoo"],
      features: {
        interval_L: ["times.aday", "13-14"],
        order_L: "order.partly",
        duration_L: ["duration.minutes", "15"],
      },

      timetables: "korponorrskata",
    },

    nagukorpo: {
      name: "Nagu - Korpo",
      name_fi: "Nauvo - Korppoo",
      specifier: "",
      piers: ["Pärnäs", "Retais"],
      operator: "finferries",
      vessels: ["l317", "prostvik1"],
      features: {
        interval_L: ["times.anhour", "1-4"],
        duration_L: ["duration.minutes", "5"],
      },

      timetables: "nagukorpo",
    },

    pargasnagu: {
      name: "Pargas - Nagu",
      name_fi: "Parainen - Nauvo",
      specifier: "",
      piers: ["Lillmälö", "Prostvik"],
      operator: "finferries",
      vessels: ["elektra", "altera", "sterna"],
      features: {
        interval_L: ["times.anhour", "1-4"],
        duration_L: ["duration.minutes", "10"],
      },

      timetables: "pargasnagu",
    },

    nauvohanka: {
      name: "Lilla ringvägen",
      name_fi: "Pieni rengastie",
      specifier: "Nagu - Själö - Hanka",
      specifier_fi: "Nauvo - Seili - Hanka",
      piers: ["Nagu", "Seili", "Hanka"],
      operator: "sinv",
      vessels: ["ostern"],
      features: {
        interval_L: ["times.aday", "3-4"],
        duration_L: ["duration.minutes", "60"],
        seasonal_L: "seasonal.summers",
        cost_L: "cost.applies",
      },
      // notes: [ {content: "In September Fri - Sun only", content_sv: "I september bara fre - sön", content_fi: "Syyskuussa ainoastaan pe - su" }],
      timetables: ["nauvohanka"],
    },
    velkuataivassalo: {
      name: "Velkuan reitti",
      name_sv: "Velkua rutt",
      name_en: "Velkua route",
      specifier: "Teersalo - Hakkenpää",
      piers: ["Teersalo", "Hakkenpää"],
      operator: "finferries",
      vessels: ["mskaita"],
      features: {
        interval_L: ["times.aday", "1-2"],
        duration_L: ["duration.minutes", "50"],
        seasonal_L: "seasonal.summers",
        seealso_fi: 'Osa <a href="#velkuanreitti">Velkuan reittiä</a>',
        seealso_sv: 'Del av <a href="#velkuanreitti">Velkua rutt</a>',
        seealso_en: 'Part of <a href="#velkuanreitti">Velkua route</a>',
        limit_L: "limit.mc_bikes_only"
      },

      timetables: "velkuataivassalo",
    },

    kasnashitis: {
      name: "Kasnäs - Hitis",
      name_fi: "Kasnäs - Hiittinen",
      specifier: "",
      piers: ["Kasnäs", "LångnäsH"],
      operator: "finferries",
      vessels: ["aurora"],
      features: {
        interval_L: ["times.aday", "4-8"],
        duration_L: ["duration.minutes", "25"],
      },
      timetables: "kasnashitis",
    },
    velkuanreitti: {
      name: "Velkuan reitti",
      name_sv: "Velkua rutt",
      name_en: "Velkua Route",
      specifier: "",
      piers: ["Teersalo", "Rauhala", "Lailuoto", "Talosmeri", "Munninmaa", "Tammisluoto", "Liettinen", "Kettumaa", "Hakkenpää"],
      operator: "finferries",
      vessels: ["mskaita"],
      features: {
        interval_L: ["times.aday", "3-9"],
        order_L: "order.partly",
        duration_L: ["duration.hours", "1-2", "Teersalo - Teersalo"],
        seasonal_L: ["seasonal.summerspier", "Hakkenpää"],
        seealso_L: ["seealso", "#velkuataivassalo", "Teersalo - Hakkenpää"],
      },
      timetables: "velkuanreitti",
    },
    rymattylanreitti: {
      name: "Rymättylän reitti",
      name_sv: "Rimito rutt",
      name_en: "Rymättylä Route",
      specifier: "",
      piers: ["Haapala", "Ruotsalainen", "Korvenmaa", "Pyytti", "Pakinainen", "Pähkinäinen", "Samsaari", "Maisaari"],
      operator: "meritie",
      vessels: ["isla"],
      features: {
        interval_L: ["times.aday", "3-5"],
        order_L: "order.partly",
        duration_L: ["duration.minutes", "40", "Haapala-Pakinainen"],
      },
      timetables: "rymattylanreitti",
    },
    korporutt: {
      name: "Korppoon reitti",
      name_sv: "Korpo rutt",
      name_en: "Korpo Route",
      specifier: "",
      piers: ["Verkan", "Finnö", "Käldersö", "Elvsö", "BerghamnK", "Luk", "Kittuis", "Lillpensor", "Storpensor", "Havträsk", "Brunskär", "Österskär", "Kälö"],
      operator: "al",
      vessels: ["fisko"],
      features: {
        interval_L: ["times.adayaweek", "0-4", "Österskär", "2"],
        order_L: "order.only",
        duration_L: ["duration.minutes", "65", "Verkan - Berghamn"],
      },
      timetables: "korporutt",
    },
    houtskarrutt: {
      name: "Houtskarin reitti ja Iniön lisäreitti",
      name_sv: "Houtskär rutt och Iniö tilläggsrutt",
      name_en: "Houtskär Route and Iniö Additional Route",
      specifier: "",
      piers: ["Näsby","Roslax","Ytterstö","Lempmo","Salmis","Lammholm","Norrby","Sördö","Lempnäs","Äpplö","Bockholm", "Södö", "Nåtö","TorsholmaI","Själö","Härklot","Kvarnholm","Åselholm","Perkala","PerkalaP","Kolko","Kannvik"],
      operator: "finferries",
      vessels: ["msfinno", "mskivimo"],
      features: {
        interval_L: ["times.aday", "1-4"],
        order_L: "order.only",
        duration_L: ["duration.hoursminutes", "2", "20", "Roslax - Torsholma"],
      },
      timetables: ["houtskarrutt", "iniorutt"]
    },

    utorutt: {
      name: "Utön reitti",
      name_sv: "Utö rutt",
      name_en: "Utö Route",
      specifier: "",
      piers: ["Pärnäs", "Berghamn", "Nötö", "Aspö", "Jurmo", "Utö"],
      operator: "meritie",
      vessels: ["baldur"],
      features: {
        interval_L: ["times.aweek", "5-6"],
        duration_L: ["duration.hours", "4.5-5.5"],
      },
      notes: [ {content: "Bus connection in Pärnäs", content_sv: "Bussförbindelse i Pärnäs", content_fi: "Linja-autoyhteys Pärnäisissä" }],
      timetables: ["utorutt"],
    },

    nagunorra: {
      name: "Nagu norra rutt",
      name_fi: "Nauvon pohjoinen reitti",
      name_en: "Nagu Northern Route",
      specifier: "",
      piers: ["Nagu", "Seili", "Innamo", "Järvsor", "Maskinnamo", "Åvensor", "Lavarn"],
      operator: "finferries",
      vessels: ["msinnamo"],
      features: {
        interval_L: ["times.aday", "1-2"],
        order_L: "order.partly",
        duration_L: ["duration.hours", "2", "Nagu - Åvensor"],
        duration_fi: "Nauvo - Ahvensaari 2 tuntia",
      },
      // notes: [
      // { 
      //   content: "<div class=\"alert alert-danger\"><strong>Note!</strong> During the re-construction of Nagu harbour (spring 2018), Keso Varvet is used instead</div>",
      //   content_fi: "<div class=\"alert alert-danger\"><strong>Huom!</strong> Nauvon sataman muutostöiden ajan (kevät 2018) liikennöidään Keson telakalta</div>",
      //   content_sv: "<div class=\"alert alert-danger\"><strong>Obs!</strong> Under Nagu hamns renovering (vår 2018), används Keso varvet i stället</div>",
      // }
      // ],
      timetables: "nagunorra",
    },

    nagutvar: {
      name: "Nauvon poikittainen reitti",
      name_sv: "Nagu tvärgående rutt",
      name_en: "Nagu Cross Route",
      specifier: "",
      piers: ["Pärnäs", "Krok", "Mattnäs", "Lånholm", "Fagerholm", "Killingholm", "Ängsö", "Tveskiftsholm", "Berghamn", "Hummelholm", "Rockelholm", "Ytterstholm", "Byskär", "Brännskär", "Grötö", "Stenskär", "Gullkrona", "Kirjais"],
      operator: "finferries",
      vessels: ["myrskylintu", "cheri"],
      features: {
        interval_L: ["times.aweek", "3"],
        order_L: ["order.only"],
        duration_L: ["duration.hoursminutes", "2", "30"], 
      },
      timetables: ["nagutvar"],
    },

    nagusodra: {
      name: "Nauvon eteläinen reitti",
      name_sv: "Nagu södra rutt",
      name_en: "Nagu Southern Route",
      specifier: "",
      piers: ["Kirjais", "PensarL", "Peno", "Brännskär", "Stenskär", "Gullkrona", "Grötö", "Knivskär", "Kopparholm", "Träskholm", "Bodö", "Björkö", "Gloskär", "Trunsö", "Sandholm", "Lökholm", "Borstö"],
      operator: "finferries",
      vessels: ["falko"],
      features: {
        interval_L: ["times.adayaweek", "1-3", "Borstö", "4"],
        order_L: ["order.only"],
        duration_L: ["duration.hours", "3-5", "Kirjais - Borstö"],
      },
      timetables: ["nagusodra"],
    },

    pargasrutt: {
      name: "Paraisten reitti",
      name_sv: "Pargas rutt",
      name_en: "Pargas Route",
      specifier: "",
      piers: ["Granvik", "Granholmen", "Heisala", "Björkholm", "Ramsholm", "Aspholm", "Stenholm", "ÖstraTallholm", "Kuggö", "PensarI"],
      operator: "finferries",
      vessels: ["viken"],
      features: {
        interval_L: ["times.aday", "3-8"],
        order_L: ["order.partly"],
        duration_L: ["duration.minutes", "60", "Granvik - Pensar"],
      },
      timetables: ["pargasrutt"],
    },

    hitisrutt: {
      name: "Hiittisten reitti",
      name_sv: "Hitis rutt",
      name_en: "Hitis Route",
      specifier: "",
      piers: ["Kasnäs", "Tunnhamn", "Vänö", "Holma", "Helsingholm", "Örö", "ÖröP", "Ängesö", "Bolax", "Bötesö", "Grönvik", "Djupö", "Vänoxaby", "Vänoxasläten", "Biskopsö", "Dalsbruk"],
      operator: "meritie",
      vessels: ["stellahiittinen", "alva"],
      features: {
        interval_L: ["times.aday", "1-3"],
        order_L: ["order.partly"],
        duration_L: ["duration.minutes", "60", "Kasnäs - Vänö"],
      },
      timetables: ["hitisstella", "hitisalva"],
    },

    hogsara: {
      name: "Högsåra",
      piers: ["Svartnäs", "Högsåra"],
      operator: "finferries",
      vessels: ["hogsara"],
      features: {
          interval_L: ["times.aday", "4-11"]
      },
      timetables: ["hogsara"]
    },
    vartsala: {
      name: "Vartsala",
      piers: ["Kivimaa", "Vartsala"],
      operator: "finferries",
      vessels: ["vartsala"],
      features: {
          interval_L: ["times.dayminutesnightondemand", "20-40"]
      },
      timetables: ["vartsala"]
    },
    vano: {
      name: "Våno",
      piers: ["Våno", "Mielisholm"],
      operator: "finferries",
      vessels: ["vano"],
      features: {
          interval_L: ["times.dayminutesnightondemand", "15-30"]
      },
      timetables: ["vano"]
    },
    hogsar: {
      name: "Högsar",
      piers: ["Grännäs", "Ängholm"],
      operator: "finferries",
      vessels: ["hogsar"],
      features: {
          interval_L: ["times.ondemandwithpauses", "9.00-9.20", "11.40-12.00", "17.00-17.20", "19.30-19.50"]
      },
      timetables: ["hogsar"]
    },
    kokkila: {
      name: "Kokkila",
      piers: ["Kokkila", "Angelniemi"],
      operator: "finferries",
      vessels: ["kokkila"],
      features: {
          interval_L: ["times.dayminutesnightondemand", "20-30"]
      },
      timetables: ["kokkila"]
    },
    hammaronsalmi: {
      name: "Hämmärönsalmi",
      piers: ["Airismaa", "Aasla"],
      operator: "finferries",
      vessels: ["hammaronsalmi"],
      features: {
          interval_L: ["times.dayminutesnightondemand", "20"]
      },
      timetables: ["hammaronsalmi"]
    },
    palva: {
      name: "Palva",
      piers: ["Teersalo", "PalvaI"],
      operator: "finferries",
      vessels: ["palva"],
      features: {
          interval_L: ["times.dayminutesnightonorder", "30-60"],
          order_L: ["order.nighttime"]
      },
      timetables: ["palva"]
    },
    velkuanmaa: {
      name: "Velkuanmaa",
      piers: ["PalvaL", "Velkuanmaa"],
      operator: "finferries",
      vessels: ["velkuanmaa"],
      features: {
          interval_L: ["times.dayminutesnightonorder", "30-60"],
          order_L: ["order.nighttime"]
      },
      timetables: ["velkuanmaa"]
    },
    kivimo: {
      name: "Kivimo",
      piers: ["Roslax", "Kivimo"],
      operator: "finferries",
      vessels: ["kivimolossi"],
      features: {
          interval_L: ["times.ondemandwithpauses", "9.10-9.30", "11.40-12.00", "17.10-17.30", "20.10-20.30"]
      },
      timetables: ["kivimo"]
    },
    saverkeit: {
      name: "Saverkeit",
      piers: ["NäsbyI", "Saverkeit"],
      operator: "finferries",
      vessels: ["saverkeit"],
      features: {
          interval_L: ["times.ondemandwithpauses", "9.10-9.30", "11.40-12.00", "17.10-17.30", "20.10-20.30"]
      },
      timetables: ["saverkeit"]
    },
    mossala: {
      name: "Mossala",
      piers: ["BjörköH", "MossalaE"],
      operator: "finferries",
      vessels: ["mossala"],
      features: {
          interval_L: ["times.ondemandwithpauses", "9.10-9.30", "11.40-12.00", "17.10-17.30", "20.10-20.30"]
      },
      timetables: ["mossala"]
    },
    keistio: {
      name: "Keistiö",
      piers: ["Dalen", "Keistiö"],
      operator: "finferries",
      vessels: ["keistio"],
      features: {
          interval_L: ["times.aday", "13-17"],
          order_L: ["order.partly"],
      },
      timetables: ["keistio"]
    },

    angosundslinjen: {
      name: "Ängösundslinjen",
      piers: ["Norrboda", "Ängö"],
      operator: "alandstrafiken",
      vessels: ["angosundslinjen"],
      features: {
          interval_L: ["times.ondemandcheckpauses"],
          order_L: ["order.nighttime"]
      },
      timetables: ["alandsvajerfarjor"]
    },
    bjorkolinjen: {
      name: "Björkölinjen",
      piers: ["LappoL", "BjörköK"],
      operator: "alandstrafiken",
      vessels: ["bjorkolinjen"],
      features: {
          interval_L: ["times.ondemandcheckpauses"],
          order_L: ["order.nighttime"]
      },
      timetables: ["alandsvajerfarjor"]
    },
    simskalalinjen: {
      name: "Simskälalinjen",
      piers: ["Sandö", "Simskäla"],
      operator: "alandstrafiken",
      vessels: ["simskalalinjen"],
      features: {
          interval_L: ["times.ondemandcheckpauses"],
      },
      timetables: ["alandsvajerfarjor"]
    },
    seglingelinjen: {
      name: "Seglingelinjen",
      piers: ["Snäckö", "Seglinge"],
      operator: "alandstrafiken",
      vessels: ["seglingelinjen"],
      features: {
          interval_L: ["times.ondemandcheckpauses"],
          duration_L: ["duration.minutes", "7"],
      },
      notes: [
      //   {
      //   content: "<div class=\"alert alert-warning\"><strong>Note!</strong> From Jun 1 to Aug 31 runs between 6 AM and 10 PM with schedule every ~30 minutes, nighttime runs on demand</div>",
      //   content_fi: "<div class=\"alert alert-warning\"><strong>Huom!</strong> 1.6.-31.8. liikennöidään päivällä klo 6-22 aikataulun mukaan n. 30 minuutin välein, yöllä tarvittaessa</div>",
      //   content_sv: "<div class=\"alert alert-warning\"><strong>Obs!</strong> 1.6.-31.8. trafikeras dagtid kl 6-22 enligt tidtabellen varje ca. 30 minuter, nattetid vid behov</div>",
      // }
    ],
      timetables: ["alandsvajerfarjor"]
    },
    toftolinjen: {
      name: "Töftölinjen",
      piers: ["Prästö", "Töftö"],
      operator: "alandstrafiken",
      vessels: ["toftolinjen"],
      features: {
        interval_L: ["times.dayminutesnightondemand", "10-50"],
        duration_L: ["duration.minutes", "4"],
      },
      timetables: ["toftolinjen"]
    },
    embarsundslinjen: {
      name: "Embarsundslinjen",
      piers: ["Finholma", "Jyddö"],
      operator: "alandstrafiken",
      vessels: ["embarsundslinjen"],
      features: {
          interval_L: ["times.ondemandcheckpauses"],
      },
      timetables: ["alandsvajerfarjor"]
    },

    skarpnatosnacko: {
      name: "Polkupyörälautta Skarpnåtö - Snäckö",
      name_sv: "Cykelfärja Skarpnåtö - Snäckö",
      name_en: "Bicycle ferry Skarpnåtö - Snäckö",
      piers: ["Skarpnåtö", "SnäcköGeta"],
      operator: "skarpnato",
      vessels: ["silvana"],
      features: {
          interval_L: ["times.aweek", "6"],
          order_L: ["order.extra"],
          duration_L: ["duration.minutes", "25"],
          seasonal_L: ["seasonal.summers"],
          cost_L: ["cost.applies"],
      },
      timetables: ["skarpnatosnacko"]
    },

    skagen: {
      name: "Skagen",
      piers: ["Skagen", "JumoE"],
      operator: "kymensaaristoliikenne",
      vessels: ["skagen"],
      features: {
        interval_fi: "Liikennöi tarvittessa ma-to 6.00-22.00, pe 6.00-23.00, la 7.00-23.00, su 8.30-20.00. Tauot 9.40-9.52, 11.58-12.10, 18.20-18.32.",
        interval_sv: "Trafikerar enligt behov må-to 6.00-22.00, fr 6.00-23.00, lö 7.00-23.00, sö 8.30-20.00. Pauser 9.40-9.52, 11.58-12.10, 18.20-18.32.",
        interval_en: "Runs when needed Mon-Thu 6AM-10PM, Fri 6AM-11PM, Sat 7AM-11PM, Sun 8:30AM-8PM. Breaks 9:40-9:52, 11:58-12:10, 18:20-18:32",
      },
      notes: [
      { 
        content_fi: "<div>Lossi lähtee Skagenista aina 15 ja 30 min ennen Auroran lähtöä Kannvikista Heponiemeen (Kustavi).</div>",
        content_sv: "<div>Färjan  avgår från Skagen alltid 15 och 30 min före Auroras avgång från Kannvik till Heponimi (Gustavs).</div>",
        content_en: "<div>The ferry departures from Skagen always 15 and 30 minutes before Aurora's departure from Kannvik to Heponiemi (Kustavi).</div>"
      }
      ],
      timetables: ["skagen"]
    },
    sorpo: {
      name: "Sorpo",
      piers: ["Jermo", "Sorpo"],
      operator: null,
      vessels: ["sorpo"],
      features: {
        interval_fi: "Liikennöi tarvittessa ma-pe 6.00-22.00, la 7.00-22.00, su 8.00-22.00. Tauot 8.30-8.50, 11.00-11.30, 16.30-16.50, 19.00-19.30.",
        interval_sv: "Trafikerar enligt behov må-fr 6.00-22.00, lö 7.00-22.00, sö 8.00-22.00. Pauser 8.30-8.50, 11.00-11.30, 16.30-16.50, 19.00-19.30.",
        interval_en: "Runs when needed Mon-Fri 6AM-10PM, Sat 7AM-10PM, Sun 8AM-10PM. Breaks 8:30-8:50, 11:00-11:30, 16.:0-16:50, 19:00-19:30",
      },
      timetables: ["sorpo"]
    },
    pettu: {
      name: "Pettu",
      piers: ["Ulkoluoto", "Pettu"],
      operator: null,
      vessels: ["pettu"],
      features: {
        interval_fi: "Liikennöi 15 minuutin välein klo 7.30-19.30.",
        interval_sv: "Trafikerar varje 15 minuter kl 7.30-19.30.",
        interval_en: "Runs every 15 minutes between 7.30 AM and 7.30 PM",
      },
      timetables: ["pettu"]
    },

    hankokasnas: {
      obsolete: true,
      name: "Hanko - Kasnäs",
      name_sv: "Hangö - Kasnäs",
      piers: ["Hanko", "Vikare", "Kasnäs"],
      operator: "wilsoncharter",
      vessels: ["sissel"],
      features: {
        interval_L: ["times.aweek", "3"],
        cost_L: "cost.applies",
        duration_L: ["duration.hours", "2"],
        seasonal_L: "seasonal.summers",
      },
      timetables: ["hankokasnas"]
    },
    // hankokasnasuto: {
    //   name: "Hanko - Kasnäs/Söderlångvik/Örö",
    //   name_sv: "Hangö - Kasnäs/Söderlångvik/Örö",
    //   name_en: "Hanko - Kasnäs/Söderlångvik/Örö",
    //   piers: ["Hanko", "Vikare", "Kasnäs", "Söderlångvik", "Örö"],
    //   operator: "hankolines",
    //   vessels: ["falken"],
    //   features: {
    //     interval_L: ["times.aweek", "3"],
    //     cost_L: "cost.applies",
    //     duration_L: ["duration.hours", "2"],
    //     seasonal_L: "seasonal.summers",
    //   },
    //   timetables: ["hankokasnasuto"]
    // },
    kasnasoro: {
      name: "Kasnäs - Örö",
      piers: ["Kasnäs", "Örö"],
      operator: ["wilsoncharter"],
      vessels: ["idun", "sissel", "minandra"],
      features: {
        interval_L: ["times.aday", "1"],
        cost_L: "cost.applies",
        duration_L: ["duration.minutes", "45"],
        seasonal_L: "seasonal.summers",
      },
      timetables: ["kasnasorowilson"]
    },
    kasnasbengtskar: {
      name: "Kasnäs - Bengtskär",
      piers: ["Kasnäs", "Rosala", "Bengtskär"],
      operator: "wilsoncharter",
      vessels: ["sissel", "minandra"],
      features: {
        interval_L: "times.onceaday",
        cost_L: "cost.applies",
        duration_L: ["duration.hourminutes", "10"],
        seasonal_L: "seasonal.summers",
      },
      timetables: ["kasnasbengtskar"]
    },
    hankobengtskar: {
      name: "Hanko - Bengtskär",
      name_sv: "Hangö - Bengtskär",
      piers: ["Hanko", "Bengtskär"],
      operator: "marinelines",
      vessels: ["summersea"],
      features: {
        interval_L: "times.onceaday",
        cost_L: "cost.applies",
        duration_L: ["duration.hourminutes", "30"],
        seasonal_L: "seasonal.summers",
      },
      timetables: ["hankobengtskar"]
    },
    utoexpress: {
      name: "Utö Express",
      specifier_fi: "Pärnäinen - Utö",
      specifier: "Pärnäs - Utö",
      piers: ["Pärnäs", "Utö"],
      operator: "al",
      vessels: ["utoexpress"],
      features: {
        interval_L: ["times.aweek", "3"],
        cost_L: "cost.applies",
        duration_L: ["duration.hoursminutes" , "1", "30"],
        seasonal_L: "seasonal.summers",
      },
      timetables: ["utoexpress"]
    },
    saaristolinja_turkunauvo: {
      name: "Saaristolinja / Skärgårdslinjen",
      specifier_fi: "Turku - Seili - Nauvo",
      specifier_sv: "Åbo - Själö - Nagu",
      specifier_en: "Turku - Själö - Nagu",
      piers: ["TurkuVitharun", "Seili", "Nagu"],
      operator: "vitharun",
      vessels: ["norrskar"],
      features: {
        interval_L: "times.onceaday",
        cost_L: "cost.applies",
        duration_L: ["duration.hoursminutes" , "2", "15"],
        seasonal_L: "seasonal.summers",
      },
      timetables: ["saaristolinja"]
    },
    saaristolinja_roolaseili: {
      name: "Saaristolinja / Skärgårdslinjen",
      specifier_fi: "Röölä - Seili - Nauvo",
      specifier: "Röölä - Själö - Nagu",
      piers: ["Röölä", "Seili", "Nagu"],
      operator: "vitharun",
      vessels: ["vidskar"],
      features: {
        interval_L: ["times.aday", "2"],
        cost_L: "cost.applies",
        duration_L: ["duration.hoursminutes" , "1", "45"],
        seasonal_L: "seasonal.summers",
      },
      timetables: ["saaristolinja"]
    },
    naantalikustavi: {
      obsolete: true,
      name: "Naantali - Velkua - Taivassalo - Kustavi",
      name_sv: "Nådendal - Velkua - Tövsala - Gustavs",
      piers: ["NaantaliVanhakaupunki", "Merimasku", "Teersalo", "Hakkenpää", "Parattula", "Kivimaa2"],
      operator: "airistonvesibussit",
      vessels: ["aavatar"],
      features: {
        interval_fi: "Liikennöi kolmena lauantaina: 7.7., 14.7., 4.8.",
        interval_sv: "Trafikerar på tre lördagar: 7.7., 14.7., 4.8.",
        interval_en: "Operates on three Saturdays: Jul 7, Jul 14, Aug 4",
        cost_L: "cost.applies",
        duration_L: ["duration.hoursminutes", "3", "15"],
        seasonal_L: "seasonal.summers",
      },
      timetables: ["naantalikustavi"]
    },
    korpostromoro: {
      obsolete: true,
      name: "Korpoström - Aspö - Vänö - Örö",
      piers: ["Korpoström", "Aspö", "Nötö", "Bodö", "Vänö", "Örö"],
      operator: "aspocharter",
      vessels: ["amanda"],
      features: {
        cost_L: "cost.applies",
        duration_L: ["duration.hours", "3 - 3.5"],
        order_L: "order.only",
        seasonal_L: "seasonal.summers",
      },
      timetables: ["korpostromoro"]
    }
  },

  lauttaLegs: [
  { id: 1, name: 'Naantali - Airisto', 
  path: "22.0399475,60.4572178,0.0 22.0845795,60.4426562,0.0 22.077713,60.4307989,0.0 22.1003723,60.3836657,0.0" },
  { id: 2, name: "Turku - Airisto",
  path: "22.219162,60.4370668,0.0 22.1728134,60.420971,0.0 22.1525574,60.4218183,0.0 22.1285248,60.4143609,0.0 22.1003723,60.3836657,0.0" },
  { id: 3, name: "Airisto - Järsö",
  path: "22.1003723,60.3836657,0.0 22.0124817,60.2759193,0.0 21.5132904,60.1995684,0.0 21.2255859,60.1001145,0.0 20.6433105,60.1014836,0.0 20.5176544,60.1309056,0.0 20.3768921,60.0949798,0.0" },
  { id: 4, name: "Järsö - Långnäs",
  path: "20.3768921,60.0949798,0.0 20.2997518,60.1170478,0.0" },
  { id: 5, name: "Järsö - Herröskatan",
  path: "20.1375961,59.9568151,0.0 20.185318,59.9679858,0.0 20.2611923,60.0075683,0.0 20.3768921,60.0949798,0.0" },
  { id: 6, name: "Herröskatan - Mariehamn",
  path: "19.9276543,60.0920271,0.0 19.9265383,60.0896932,0.0 19.9267959,60.0724635,0.0 19.9263668,60.0541738,0.0 19.9403572,60.0321012,0.0 19.9405289,60.0009602,0.0 20.0013828,59.971551,0.0 20.0325394,59.9568581,0.0 20.1375961,59.9568151,0.0" },
  { id: 7, name: "Herröskatan - Hanko",
  path: "20.1375961,59.9568151,0.0 20.1618004,59.9589636,0.0 20.1935577,59.9587917,0.0 20.3082275,59.9231945,0.0 20.5149078,59.8009796,0.0 21.6616058,59.70,0.0 23.6027527,59.70,0.0" },
  { id: 8, name: "Herröskatan - Fejan",
  path: "19.1717434,59.7310521,0.0 19.342804,59.7643486,0.0 20.1375961,59.9568151,0.0" },
  { id: 9, name: "Mariehamn - Fejan",
  path: "19.1717434,59.7310521,0.0 19.3379974,59.766596,0.0 19.5910263,59.8808408,0.0 19.8796749,60.0355309,0.0 19.9230194,60.0727205,0.0 19.924907,60.090806,0.0 19.9276543,60.0920271,0.0" },
  { id: 10, name: "Fejan - Kapellskär",
  path: "19.0666008,59.722831,0.0 19.0717506,59.7218789,0.0 19.1717434,59.7310521,0.0" },
  { id: 11, name: "Fejan - Stockholm",
  path: "18.2084656,59.3335396,0.0 18.2654572,59.3583959,0.0 18.2984161,59.3772885,0.0 18.3746338,59.3695928,0.0 18.4384918,59.3531461,0.0 18.4501648,59.3580459,0.0 18.4501648,59.3975688,0.0 18.3904266,59.4325064,0.0 18.3952332,59.4391405,0.0 18.4309387,59.4461223,0.0 18.453598,59.4841479,0.0 18.5572815,59.5336217,0.0 18.6602783,59.5684189,0.0 18.7447357,59.5826754,0.0 18.9541626,59.6698211,0.0 19.0447998,59.6975491,0.0 19.1717434,59.7310521,0.0" },
  { id: 12, name: "Stockholm Värtan",
  path: "18.108902,59.3503459,0.0 18.1281281,59.3505209,0.0 18.1614304,59.3380922,0.0 18.2084656,59.3335396,0.0" },
  { id: 13, name: "Stockholm Stadsgården",
  path: "18.0965424,59.3170755,0.0 18.1075287,59.318477,0.0 18.1597137,59.3205792,0.0 18.2084656,59.3335396,0.0" },
  { id: 14, name: "Grisslehamn - Eckerö",
  path: "19.535583,60.225623,0.0 19.5304298,60.2283061,0.0 19.5201302,60.226857,0.0 19.4531822,60.1805383,0.0 18.8297379,60.094225,0.0 18.8154602,60.0981463,0.0" },
  { id: 15, name: "Hanko - Helsinki",
  path: "23.6027527,59.70,0.0 24.8881531,59.9869673,0.0 24.9904633,60.1510752,0.0 24.9568176,60.1661089,0.0" },
  { id: 16, name: "Hanko - Tallinn",
  path: "23.6027527,59.70,0.0 24.555864,59.632669,0.0 24.784230,59.456251,0.0 24.770607,59.443868,0.0" },
  ],

  lauttaRoutes: [
  { sname: "Turku - Maarianhamina/Långnäs - Tukholma", 
    sname_sv: "Åbo - Mariehamn/Långnäs - Stockholm",
    sname_en: "Turku - Mariehamn/Långnäs - Stockholm",
    operators: ["Viking"], legs: [2, 3, 4, 5, 6, 8, 9, 11, 13],
    description_fi: "2 kertaa päivässä, kesto n. 11 tuntia",
    description_sv: "2 gånger om dagen, längd ca 11 timmar",
    description_en: "twice a day, duration about 11 hours"},
  { sname: "Turku - Maarianhamina/Långnäs - Tukholma", 
    sname_sv: "Åbo - Mariehamn/Långnäs - Stockholm",
    sname_en: "Turku - Mariehamn/Långnäs - Stockholm",
    operators: ["Silja"], legs: [2, 3, 4, 5, 6, 8, 9, 11, 12],
    description_fi: "kerran päivässä, kesto n. 11 tuntia",
    description_sv: "en gång om dagen, längd ca 11 timmar",
    description_en: "once a day, duration about 11 hours"},
  { sname: "Helsinki - Maarianhamina - Tukholma",
    sname_sv: "Helsingfors - Mariehamn - Stockholm",
    sname_en: "Helsinki - Mariehamn - Stockholm",
    operators: ["Viking"], legs: [7, 6, 9, 11, 13, 15],
    description_fi: "kerran päivässä, kesto n. 17,5 tuntia",
    description_sv: "en gång om dagen, längd ca 17,5 timmar",
    description_en: "once a day, duration about 17,5 hours"},
  { sname: "Helsinki - Maarianhamina - Tukholma",
    sname_sv: "Helsingfors - Mariehamn - Stockholm",
    sname_en: "Helsinki - Mariehamn - Stockholm",
    operators: ["Silja"], legs: [7, 6, 9, 11, 12, 15],
    description_fi: "kerran päivässä, kesto n. 17,5 tuntia",
    description_sv: "en gång om dagen, längd ca 17,5 timmar",
    description_en: "once a day, duration about 17,5 hours"},
  { sname: "Tallinna - Maarianhamina - Tukholma",
    sname_sv: "Tallinn - Mariehamn - Stockholm",
    sname_en: "Tallinn - Mariehamn - Stockholm",
    operators: ["Tallink"], legs: [7, 6, 9, 11, 12, 16],
    description_fi: "kerran kahdessa päivässä, kesto n. 17,5 tuntia",
    description_sv: "en gång om två dagar, längd ca 17,5 timmar",
    description_en: "every other day, duration about 17,5 hours"},
  // { sname: "Mariehamn - Stockholm",
  //   sname_fi: "Maarianhamina - Tukholma",
  //   operators: ["Viking"], legs: [9, 11, 13],
  //   description_fi: "kerran päivässä, kesto 7-12 tuntia",
  //   description_sv: "en gång om dagen, längd 7-12 timmar",
  //   description_en: "once a day, duration 7-12 hours"},
  // { sname: "Kapellskär - Mariehamn",
  //   sname_fi: "Kapellskär - Maarianhamina",
  //   operators: ["Viking"], legs: [9, 10],
  //   description_fi: "2-3 kertaa päivässä, kesto n. 2,5 tuntia, linja-autoyhteys Tukholmaan",
  //   description_sv: "2-3 gånger om dagen, längd ca 2,5 timmar, bussförbindelse till Stockholm",
  //   description_en: "2-3 times a day, duration about 2.5 hours, bus connection to Stockholm"},
  { sname: "Eckerö - Grisslehamn", operators: ["Eckerolinjen"], legs: [14],
    description_fi: "2-3 kertaa päivässä, kesto n. 2 tuntia",
    description_sv: "2-3 gånger om dagen, längd ca 2 timmar",
    description_en: "2-3 times a day, duration about 2 hours"},
  { sname: "Naantali - Långnäs - Kapellskär",
    sname_sv: "Nådendal - Långnäs - Kapellskär",
    operators: ["Finnlines"], legs: [1, 3, 4, 5, 8, 10],
    description_fi: "2 kertaa päivässä, kesto n. 8,5 tuntia",
    description_sv: "2 gånger om dagen, längd ca 8,5 timmar",
    description_en: "twice a day, duration about 8.5 hours"},
  ],
  lauttaOperators: {
    Viking: {name: "Viking Line", logo: "img/vikingline.png", height: 15, link: "https://www.vikingline.fi/"},
    Silja: {name: "Tallink / Silja Line", logo: "img/siljaline.png", height: 20, link: "https://www.tallinksilja.fi/"},
    Tallink: {name: "Tallink / Silja Line", logo: "img/tallink.png", height: 20, link: "https://www.tallink.ee/"},
    Finnlines: {name: "Tallink / Silja Line", logo: "img/finnlines.png", height: 20, link: "https://www.finnlines.com/"},
    Eckerolinjen: {name: "Eckerölinjen", logo: "img/eckerolinjen.png", height: 20, link: "https://www.eckerolinjen.ax/"}
  }
}

function prepareData(data) {
  Object.keys(data.mun).forEach(function(key) {
    var m = data.mun[key];
    m.name = m.name? m.name: key;
  });

  Object.keys(data.piers).forEach(function(key) {
    var pier = data.piers[key];
    pier.id = key;
    pier.name = pier.name? pier.name: key;
    pier.mun = data.mun[pier.mun];
    pier.type = pier.type? pier.type: "2";
  });

  Object.keys(data.routes).forEach(function(key) {
    var route = data.routes[key];
    route.id = key;
    route.piers = route.piers.map(function(pier) {
      return data.piers[pier];
    });
    route.vessels = route.vessels.map(function(vessel) {
      return data.ferries[vessel];
    });

    if (!route.operator) route.operator = [];
    if (!Array.isArray(route.operator)) route.operator = [route.operator];
    route.operator = route.operator.map(function(op) { return data.operators[op] });
    route.pricelists = data.pricelists[route.pricelists];

    if (!Array.isArray(route.timetables)) route.timetables = [route.timetables];

    route.timetables = route.timetables.map(function(timetable) {
      data.timetables[timetable].id = timetable;
      return data.timetables[timetable];
    });

  });

  var i = 0;
  data.lauttaRoutes.forEach(function(lr) { lr.id = i++; });

  Object.keys(data.mun).forEach(function(key) { addFinnishInessiivi(data.mun[key]); });
}

function addFinnishInessiivi(mun) {
  var vokaalit = "aeiouyåäö";
  var etuvokaalit = "yäö";
  if (mun.name_fi_in) return;
  var name = mun.name_fi || mun.name;
  var lastChar = name.slice(-1);
  if (vokaalit.indexOf(lastChar) < 0) name += "i";
  var isEtu = etuvokaalit.split("").map(function(ev) { return name.indexOf(ev) >= 0; }).reduce(function(x, y) { return x || y; }, false);
  name += isEtu? "ssä": "ssa";
  mun.name_fi_in = name;
}

prepareData(fdata);

console.log(JSON.stringify(fdata));
