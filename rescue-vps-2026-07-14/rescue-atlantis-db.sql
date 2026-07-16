--
-- PostgreSQL database dump
--

\restrict garGg5ErEEEYIW3rgx1gm88xAWNWYLcq9C1fNNh27hY6FfVRJYcBC4NaUWIYA2M

-- Dumped from database version 15.14 (Debian 15.14-1.pgdg13+1)
-- Dumped by pg_dump version 18.0 (Debian 18.0-1.pgdg13+3)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: crew; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crew (
    id integer NOT NULL,
    name text NOT NULL,
    role text,
    photo text,
    note text,
    is_lead boolean DEFAULT false,
    sort_order integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.crew OWNER TO postgres;

--
-- Name: crew_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.crew_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.crew_id_seq OWNER TO postgres;

--
-- Name: crew_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.crew_id_seq OWNED BY public.crew.id;


--
-- Name: testimonials; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.testimonials (
    id integer NOT NULL,
    kind text DEFAULT 'text'::text NOT NULL,
    quote text,
    author text,
    origin text,
    journey text,
    video_id text,
    caption text,
    sort_order integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.testimonials OWNER TO postgres;

--
-- Name: testimonials_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.testimonials_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.testimonials_id_seq OWNER TO postgres;

--
-- Name: testimonials_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.testimonials_id_seq OWNED BY public.testimonials.id;


--
-- Name: tours; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tours (
    id integer NOT NULL,
    slug text NOT NULL,
    name text NOT NULL,
    subtitle text,
    badge text,
    category text,
    route text,
    dates text,
    duration text,
    price text,
    for_whom text,
    image text,
    image2 text,
    blurb text,
    overview jsonb DEFAULT '[]'::jsonb,
    highlights jsonb DEFAULT '[]'::jsonb,
    itinerary jsonb DEFAULT '[]'::jsonb,
    includes jsonb DEFAULT '[]'::jsonb,
    sort_order integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.tours OWNER TO postgres;

--
-- Name: tours_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tours_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tours_id_seq OWNER TO postgres;

--
-- Name: tours_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tours_id_seq OWNED BY public.tours.id;


--
-- Name: crew id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crew ALTER COLUMN id SET DEFAULT nextval('public.crew_id_seq'::regclass);


--
-- Name: testimonials id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.testimonials ALTER COLUMN id SET DEFAULT nextval('public.testimonials_id_seq'::regclass);


--
-- Name: tours id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tours ALTER COLUMN id SET DEFAULT nextval('public.tours_id_seq'::regclass);


--
-- Data for Name: crew; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crew (id, name, role, photo, note, is_lead, sort_order, created_at, updated_at) FROM stdin;
1	Fabian	Founder · Guardian of the Atlantis Call	/crew/fabian.png	Raised in Berlin, Fabian left the corporate world for a life with the sea — weaving freediving, somatics, ritual, and the wisdom of water into transformational retreats.	t	0	2026-06-29 18:26:30.443734+00	2026-06-29 18:26:30.443734+00
2	Ambika	Transformational Guide · Yogini · Shamanic Practitioner · Sacred Feminine Work	/crew/ambika.webp	\N	f	1	2026-06-29 18:26:30.843827+00	2026-06-29 18:26:30.843827+00
3	Anna	Yoga Teacher · Cacao Facilitator · Sacred Feminine Work	/crew/anna.jpeg	\N	f	2	2026-06-29 18:26:30.943908+00	2026-06-29 18:26:30.943908+00
4	Damla	Holistic Healer · Musician · Water Therapist	/crew/damla.jpeg	\N	f	3	2026-06-29 18:26:31.043951+00	2026-06-29 18:26:31.043951+00
5	Dila	Holistic Healing Therapist · Sacred Feminine Work	/crew/dila.jpeg	\N	f	4	2026-06-29 18:26:31.243634+00	2026-06-29 18:26:31.243634+00
6	Hassan	Spiritual Guide of Upper Egypt	/crew/hassan.jpeg	\N	f	5	2026-06-29 18:26:31.344001+00	2026-06-29 18:26:31.344001+00
7	Lesya (Amrita)	Yoga Teacher · Sound Healer · Creator of Shakti Flow	/crew/lesya.jpg	\N	f	6	2026-06-29 18:26:31.443673+00	2026-06-29 18:26:31.443673+00
8	Mido	Traditional Egyptian Healer	/crew/mido.jpeg	\N	f	7	2026-06-29 18:26:31.543704+00	2026-06-29 18:26:31.543704+00
9	Miro	Breathwork Facilitator · Chi Core Bodywork · Reiki	/crew/miro.jpg	\N	f	8	2026-06-29 18:26:31.643699+00	2026-06-29 18:26:31.643699+00
10	Mohamed	Hydrotherapy Specialist & Physiotherapist	/crew/mohamed.jpeg	\N	f	9	2026-06-29 18:26:31.743736+00	2026-06-29 18:26:31.743736+00
11	Mona	Temple Keeper & Designer of Transformative Quests	/crew/mona.jpg	\N	f	10	2026-06-29 18:26:31.843737+00	2026-06-29 18:26:31.843737+00
12	Shak	Keeper of the Blue Lotus Lineage	/crew/shak.jpg	\N	f	11	2026-06-29 18:26:31.943738+00	2026-06-29 18:26:31.943738+00
\.


--
-- Data for Name: testimonials; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.testimonials (id, kind, quote, author, origin, journey, video_id, caption, sort_order, created_at, updated_at) FROM stdin;
1	video	\N	\N	\N	\N	ye27cV8erLY	A traveler shares the journey, in their own words.	0	2026-06-29 18:26:32.146129+00	2026-06-29 18:26:32.146129+00
2	video	\N	\N	\N	\N	DL_xDzdgj7U	What the retreat felt like, from someone who lived it.	1	2026-06-29 18:26:32.343918+00	2026-06-29 18:26:32.343918+00
3	video	\N	\N	\N	\N	ksTRnq-idz0	Reflections from the water and the temples.	2	2026-06-29 18:26:32.443813+00	2026-06-29 18:26:32.443813+00
4	text	I came to see the pyramids. I left having met a version of myself I’d forgotten existed. Fabian doesn’t run tours — he opens doors you didn’t know were there.	Marisol R.	Barcelona	Complete Egypt Initiation	\N	\N	3	2026-06-29 18:26:32.544533+00	2026-06-29 18:26:32.544533+00
5	text	The dolphins came to us. Genuinely the most alive eight days of my life — and the most peaceful. The Red Sea got into my blood.	James T.	London	Wild Dolphins of the Red Sea	\N	\N	4	2026-06-29 18:26:32.84543+00	2026-06-29 18:26:32.84543+00
6	text	Dawn at Giza, alone, before anyone else. I wept. There is no other way to say it. Worth every mile.	Aiko N.	Kyoto	Nile Sailing & Pyramids at Dawn	\N	\N	5	2026-06-29 18:26:32.943783+00	2026-06-29 18:26:32.943783+00
7	text	Reading the temple walls with someone who actually understands the myths changed everything. Karnak stopped being stone and started being a story I was inside of.	Dr. Helena V.	Amsterdam	Ancient Temples & River Pilgrimage	\N	\N	6	2026-06-29 18:26:33.043795+00	2026-06-29 18:26:33.043795+00
8	text	Small group, big heart, zero pretension. I arrived a stranger and left with a family scattered across four continents.	Omar K.	Toronto	Complete Egypt Initiation	\N	\N	7	2026-06-29 18:26:33.14435+00	2026-06-29 18:26:33.14435+00
9	text	Luxurious without being soulless. Every detail considered, every moment given room to breathe. This is how Egypt should be experienced.	Sophie L.	Paris	Nile Sailing & Pyramids at Dawn	\N	\N	8	2026-06-29 18:26:33.244041+00	2026-06-29 18:26:33.244041+00
\.


--
-- Data for Name: tours; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tours (id, slug, name, subtitle, badge, category, route, dates, duration, price, for_whom, image, image2, blurb, overview, highlights, itinerary, includes, sort_order, created_at, updated_at) FROM stdin;
1	complete-egypt-initiation	Complete Egypt Initiation	A Journey of Rebirth	Application · By interview	\N	Hurghada → Cairo	29 Aug – 12 Sep 2026	15 days	from $6,800	For those ready for deep transformation	https://images.unsplash.com/photo-1539768942893-daf53e448371?auto=format&fit=crop&w=2400&q=80	https://images.unsplash.com/photo-1584719763904-2799b453ba8d?auto=format&fit=crop&w=2000&q=80	Our flagship pilgrimage. From the warm shallows of the Red Sea to the foot of the Great Pyramid, this is the full arc — death and rebirth, in the only land that ever made an art of both.	["Fifteen days that move like the Egyptian soul’s own journey through the afterlife: a descent, a reckoning, and a rising into the light. We begin where the sun warms the water and end where it crowns the pyramids at dawn.", "This is the complete initiation — desert and river, temple and tomb, silence and celebration. It asks everything of you and gives back more."]	["Private dawn entry to the Giza plateau before the crowds", "A night sailing the Nile under a sky thick with stars", "Candlelit ritual within a working temple sanctuary", "Swimming the Red Sea reefs at golden hour", "A closing sharing circle beneath the desert moon"]	[{"day": "Days 1–4", "text": "Arrival, warm-water immersion, reef swims, and the slow shedding of the world you came from.", "place": "Hurghada · Red Sea"}, {"day": "Days 5–8", "text": "Temples at first light, hieroglyph readings, and the long descent into the tombs of the kings.", "place": "Luxor · Karnak & Valley of the Kings"}, {"day": "Days 9–11", "text": "Sailing felucca by day, ceremony by night, the river carrying what you’re ready to release.", "place": "The Nile · Aswan"}, {"day": "Days 12–15", "text": "The pyramids at dawn, the Sphinx’s long gaze, and a final circle to seal the rebirth.", "place": "Cairo · Giza"}]	["Boutique & sailing accommodation", "All private guiding & rituals", "Internal transfers & felucca", "Most meals", "Temple & site access"]	0	2026-06-29 18:26:29.44359+00	2026-06-29 18:26:29.44359+00
2	wild-dolphins-red-sea	Swimming with Wild Dolphins	in the Red Sea	Small group · Limited cabins	\N	Hurghada	29 Aug – 5 Sep 2026	8 days	from $3,900	For ocean lovers & sensitives	https://images.unsplash.com/photo-1607153333879-c174d265f1d2?auto=format&fit=crop&w=1600&q=80	https://images.unsplash.com/photo-1589308945435-38c3f99b3824?auto=format&fit=crop&w=2000&q=80	Meet wild spinner dolphins in their own blue cathedral. No tanks, no cages — just you, your breath, and the most charismatic locals in the Red Sea, on their terms.	["An intimate, small-cabin voyage built around respectful, free-diving encounters with wild dolphins. We move slowly, we ask permission, and the sea decides the rest.", "Between encounters: coral gardens, long quiet swims, and the kind of stillness only open water can teach."]	["Free-diving encounters with wild spinner dolphins", "Vibrant coral-reef snorkeling daily", "Breath-work to meet the sea calm and open", "Sunset deck circles under desert stars", "Tiny group, big cabins, real privacy"]	[{"day": "Days 1–2", "text": "Board, settle, and ease into the rhythm of the water with breath and orientation.", "place": "Hurghada · Embark"}, {"day": "Days 3–5", "text": "Daily dolphin encounters, coral swims, and long luminous afternoons on deck.", "place": "Offshore reefs"}, {"day": "Days 6–7", "text": "Quiet anchorages, deeper free-dives, and ceremony at sunset.", "place": "Hidden bays"}, {"day": "Day 8", "text": "A closing circle and the slow sail home, changed.", "place": "Return"}]	["Private liveaboard cabin", "Guided free-diving & snorkeling", "All meals aboard", "Breath-work sessions", "Marine guide & crew"]	1	2026-06-29 18:26:29.843863+00	2026-06-29 18:26:29.843863+00
3	ancient-temples-river-pilgrimage	Ancient Temples & River Pilgrimage	Ritual on the Sacred Nile	Small group · Limited cabins	\N	Luxor → Cairo	5 – 12 Sep 2026	8 days	from $4,400	For seekers of ancient wisdom	https://images.unsplash.com/photo-1584719763904-2799b453ba8d?auto=format&fit=crop&w=2000&q=80	https://images.unsplash.com/photo-1581248736814-67c28a550ca6?auto=format&fit=crop&w=2000&q=80	Walk the avenues the priests walked. From Karnak’s forest of columns to the secret chambers of the Valley of the Kings, this is Egypt for those who came for the deep stuff.	["A temple-by-temple pilgrimage up the sacred river — reading the walls, entering the sanctuaries, and following the old map of the soul carved in stone.", "We pair each site with quiet practice, so the wisdom doesn’t just impress you. It enters you."]	["The hypostyle hall of Karnak at first light", "Hieroglyph & mythology readings on-site", "Tomb visits in the Valley of the Kings", "A Nile sailing leg by felucca", "Closing rite among Giza’s monuments"]	[{"day": "Days 1–3", "text": "Karnak and Luxor temples, the Valley of the Kings, and evenings of reflection.", "place": "Luxor"}, {"day": "Days 4–5", "text": "Sailing between sacred sites, ritual on the water, the river as teacher.", "place": "The Nile"}, {"day": "Days 6–8", "text": "The Egyptian Museum, the pyramids, and a final ceremony beneath the Sphinx.", "place": "Cairo · Giza"}]	["Boutique & sailing stays", "Expert Egyptologist guiding", "All site access", "Most meals", "Internal transfers"]	2	2026-06-29 18:26:29.943904+00	2026-06-29 18:26:29.943904+00
4	nile-sailing-pyramids-dawn	Nile Sailing & Pyramids at Dawn	The Essential Luxury Escape	Boutique · Couples & solo	\N	Cairo · Giza · Nile	Seasonal departures · by request	6 days	from $3,200	For first-timers who refuse the ordinary	https://images.unsplash.com/photo-1680356217112-dad9300ce49d?auto=format&fit=crop&w=2000&q=80	https://images.unsplash.com/photo-1539768942893-daf53e448371?auto=format&fit=crop&w=2400&q=80	The greatest hits, done beautifully. Sail the Nile, sleep under stars, and stand before the pyramids as the first light touches the stone — a short journey that lingers for life.	["A refined introduction to Egypt for those who want the icons without the crowds and clichés. Private guiding, boutique stays, and just enough ritual to make it sacred.", "Perfect as a first journey — or a romantic one."]	["Private sunrise at the Giza pyramids", "A night aboard a traditional felucca", "The Sphinx, Saqqara, and old Cairo", "Sunset dinner overlooking the Nile", "Small, intimate group · personally guided"]	[{"day": "Days 1–2", "text": "Arrival, old Cairo, and a private dawn at the pyramids.", "place": "Cairo · Giza"}, {"day": "Days 3–4", "text": "Felucca sailing, a starlit night on the water, riverside ritual.", "place": "The Nile"}, {"day": "Days 5–6", "text": "The step pyramid, a closing toast, and departure.", "place": "Saqqara & farewell"}]	["Boutique hotel & felucca", "Private guide & driver", "Pyramid & site access", "Breakfasts & select dinners", "Airport transfers"]	3	2026-06-29 18:26:30.044004+00	2026-06-29 18:26:30.044004+00
5	somatic-water-therapy-training	Somatic Water Therapy Training	50-Hour Certification	Training · Certification	training	Red Sea · Egypt	By cohort · dates on request	50 hours	on application	For practitioners, healers & space-holders	https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=1600&q=80	https://images.unsplash.com/photo-1589308945435-38c3f99b3824?auto=format&fit=crop&w=2000&q=80	Become a holder of warm water. A 50-hour immersion in somatic water therapy — the art of meeting another person in the held weightlessness of the sea, and helping them release what words can’t reach.	["Our training isn’t a retreat you attend — it’s a craft you take home. Over fifty hours in the warm shallows of the Red Sea, you’ll learn the foundations of somatic and aquatic bodywork: breath, holds, surrender, and the quiet attunement that lets the water do its work.", "This is for those already on the path — meditators, therapists, healers, and facilitators — who want to add the medicine of water to the work they already hold."]	["Foundations of somatic & warm-water bodywork", "Breath-work and nervous-system regulation", "Holding, surrender, and trauma-informed touch", "Daily practice in the warm Red Sea", "50-hour certificate of completion"]	[{"day": "Module 1", "text": "Breath, presence, and the principles of meeting another in water. The inner work before the hands-on work.", "place": "Ground"}, {"day": "Module 2", "text": "Core holds, movement, and surrender — learning to support a body fully in warm water.", "place": "Hold"}, {"day": "Module 3", "text": "Trauma-informed practice: reading the nervous system and letting the water unwind what’s held.", "place": "Release"}, {"day": "Module 4", "text": "Putting it together into full sessions, plus how to hold this work safely for others back home.", "place": "Integrate"}]	["50-hour structured curriculum", "Daily in-water practicum", "Certificate of completion", "Course materials", "Small cohort & personal mentorship"]	4	2026-06-29 18:26:30.243685+00	2026-06-29 18:26:30.243685+00
\.


--
-- Name: crew_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crew_id_seq', 12, true);


--
-- Name: testimonials_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.testimonials_id_seq', 9, true);


--
-- Name: tours_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tours_id_seq', 5, true);


--
-- Name: crew crew_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crew
    ADD CONSTRAINT crew_pkey PRIMARY KEY (id);


--
-- Name: testimonials testimonials_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.testimonials
    ADD CONSTRAINT testimonials_pkey PRIMARY KEY (id);


--
-- Name: tours tours_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tours
    ADD CONSTRAINT tours_pkey PRIMARY KEY (id);


--
-- Name: tours tours_slug_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tours
    ADD CONSTRAINT tours_slug_key UNIQUE (slug);


--
-- PostgreSQL database dump complete
--

\unrestrict garGg5ErEEEYIW3rgx1gm88xAWNWYLcq9C1fNNh27hY6FfVRJYcBC4NaUWIYA2M

