--
-- PostgreSQL database dump
--

\restrict FV540y1umrQSow0VulByIFO43SriVzUU9vs49iJdONU2jXMc75xwG3OMO3JL0KP

-- Dumped from database version 15.14 (Debian 15.14-1.pgdg13+1)
-- Dumped by pg_dump version 15.14 (Debian 15.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
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
-- Name: content; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.content (
    key text NOT NULL,
    value jsonb NOT NULL
);


ALTER TABLE public.content OWNER TO postgres;

--
-- Name: cv_entries; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cv_entries (
    id integer NOT NULL,
    year integer,
    kind text,
    title text NOT NULL,
    venue text,
    sort_order integer DEFAULT 0
);


ALTER TABLE public.cv_entries OWNER TO postgres;

--
-- Name: cv_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.cv_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.cv_entries_id_seq OWNER TO postgres;

--
-- Name: cv_entries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.cv_entries_id_seq OWNED BY public.cv_entries.id;


--
-- Name: installations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.installations (
    id integer NOT NULL,
    show_id integer,
    image text NOT NULL,
    caption text,
    sort_order integer DEFAULT 0
);


ALTER TABLE public.installations OWNER TO postgres;

--
-- Name: installations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.installations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.installations_id_seq OWNER TO postgres;

--
-- Name: installations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.installations_id_seq OWNED BY public.installations.id;


--
-- Name: news; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.news (
    id integer NOT NULL,
    title text NOT NULL,
    date text,
    body text,
    link text,
    sort_order integer DEFAULT 0
);


ALTER TABLE public.news OWNER TO postgres;

--
-- Name: news_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.news_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.news_id_seq OWNER TO postgres;

--
-- Name: news_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.news_id_seq OWNED BY public.news.id;


--
-- Name: press; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.press (
    id integer NOT NULL,
    publication text,
    title text,
    year integer,
    image text,
    pdf_url text,
    quote text,
    sort_order integer DEFAULT 0
);


ALTER TABLE public.press OWNER TO postgres;

--
-- Name: press_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.press_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.press_id_seq OWNER TO postgres;

--
-- Name: press_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.press_id_seq OWNED BY public.press.id;


--
-- Name: shows; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shows (
    id integer NOT NULL,
    slug text NOT NULL,
    title text NOT NULL,
    gallery text,
    city text,
    year integer,
    blurb text,
    press_url text,
    sort_order integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.shows OWNER TO postgres;

--
-- Name: shows_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.shows_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.shows_id_seq OWNER TO postgres;

--
-- Name: shows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.shows_id_seq OWNED BY public.shows.id;


--
-- Name: works; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.works (
    id integer NOT NULL,
    slug text NOT NULL,
    title text NOT NULL,
    year integer,
    medium text,
    dimensions text,
    image text,
    status text,
    surface text,
    tier text,
    show_id integer,
    sort_order integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    is_hero boolean DEFAULT false
);


ALTER TABLE public.works OWNER TO postgres;

--
-- Name: works_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.works_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.works_id_seq OWNER TO postgres;

--
-- Name: works_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.works_id_seq OWNED BY public.works.id;


--
-- Name: cv_entries id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cv_entries ALTER COLUMN id SET DEFAULT nextval('public.cv_entries_id_seq'::regclass);


--
-- Name: installations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.installations ALTER COLUMN id SET DEFAULT nextval('public.installations_id_seq'::regclass);


--
-- Name: news id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.news ALTER COLUMN id SET DEFAULT nextval('public.news_id_seq'::regclass);


--
-- Name: press id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.press ALTER COLUMN id SET DEFAULT nextval('public.press_id_seq'::regclass);


--
-- Name: shows id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shows ALTER COLUMN id SET DEFAULT nextval('public.shows_id_seq'::regclass);


--
-- Name: works id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.works ALTER COLUMN id SET DEFAULT nextval('public.works_id_seq'::regclass);


--
-- Data for Name: content; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.content (key, value) FROM stdin;
bio	{"heading": "From Bogotá to a Queens studio.", "portrait": "/assets/omar-portrait.jpg", "statement": "Acrylic is poured onto wax paper and left to dry into thousands of brightly colored ovals and drips — each one finding its own edge. Once dry, every shape is hand-peeled into a unique building block, then layered onto the canvas. A brush is never used.", "paragraphs": ["Omar Chacón was born in Bogotá, Colombia and moved to the United States with his family as a child. He earned a BFA from Ringling College of Art and Design and an MFA in painting from the San Francisco Art Institute. He lives and works in Queens, New York.", "His signature method began with a memory: his self-taught grandfather painting small abstract dots. Those dots became colorful lozenges and discs — read as aerial views of people, mixing, multiplying, and taking over the surface. The work draws on the folk art and indigenous textiles of South America and the mestizo fusion of Latin American life.", "Chacón is represented by Robischon Gallery (Denver). His work has also been shown with Margaret Thatcher Projects (New York), Fouladi Projects (San Francisco), and Brunnhofer Galerie (Linz, Austria)."]}
contact	{"blurb": "For studio visits, acquisitions, and exhibition inquiries.", "email": "", "artnet": "https://www.artnet.com/artists/omar-chac%C3%B3n/", "gallery": "https://robischongallery.com/", "instagram": "https://www.instagram.com/omarchaconjr/"}
cv	{"text": ""}
\.


--
-- Data for Name: cv_entries; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cv_entries (id, year, kind, title, venue, sort_order) FROM stdin;
22	\N	represented	Robischon Gallery	Denver, CO	0
23	2017	commission	NYU Langone Art Program & Collection	New York, NY	1
24	2008	award	NYFA Artist Fellowship	New York Foundation for the Arts	2
25	2007	award	William & Dorothy Yeck Award (Juror: Jerry Saltz, Village Voice)	Miami University National Young Painters Competition	3
26	2005	award	SECA Award Nominee	San Francisco Museum of Modern Art	4
27	2004	award	Tournesol Award & Residency Finalist	Headlands Center for the Arts, Sausalito, CA	5
28	2004	education	MFA, Painting	San Francisco Art Institute, San Francisco, CA	6
29	2002	award	Jurors' Award, Best of Ringling	Ringling College of Art and Design	7
30	2002	education	BFA	Ringling College of Art and Design, Sarasota, FL	8
\.


--
-- Data for Name: installations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.installations (id, show_id, image, caption, sort_order) FROM stdin;
18	2	/assets/installations/variaciones-chuecas-2022-1.jpg	Variaciones Chuecas — Robischon Gallery, Denver, 2022	0
19	2	/assets/installations/variaciones-chuecas-2022-10.jpg	Variaciones Chuecas — Robischon Gallery, Denver, 2022	1
20	2	/assets/installations/variaciones-chuecas-2022-2.jpg	Variaciones Chuecas — Robischon Gallery, Denver, 2022	2
21	2	/assets/installations/variaciones-chuecas-2022-3.jpg	Variaciones Chuecas — Robischon Gallery, Denver, 2022	3
22	2	/assets/installations/variaciones-chuecas-2022-4.jpg	Variaciones Chuecas — Robischon Gallery, Denver, 2022	4
23	2	/assets/installations/variaciones-chuecas-2022-5.jpg	Variaciones Chuecas — Robischon Gallery, Denver, 2022	5
24	2	/assets/installations/variaciones-chuecas-2022-6.jpg	Variaciones Chuecas — Robischon Gallery, Denver, 2022	6
25	2	/assets/installations/variaciones-chuecas-2022-7.jpg	Variaciones Chuecas — Robischon Gallery, Denver, 2022	7
26	2	/assets/installations/variaciones-chuecas-2022-8.jpg	Variaciones Chuecas — Robischon Gallery, Denver, 2022	8
27	2	/assets/installations/variaciones-chuecas-2022-9.jpg	Variaciones Chuecas — Robischon Gallery, Denver, 2022	9
28	1	/assets/installations/fluid-borders-2021-1.jpg	Fluid Borders — Margaret Thatcher Projects, New York, 2021	0
29	1	/assets/installations/fluid-borders-2021-2.jpg	Fluid Borders — Margaret Thatcher Projects, New York, 2021	1
30	1	/assets/installations/fluid-borders-2021-3.jpg	Fluid Borders — Margaret Thatcher Projects, New York, 2021	2
31	1	/assets/installations/fluid-borders-2021-4.jpg	Fluid Borders — Margaret Thatcher Projects, New York, 2021	3
32	1	/assets/installations/fluid-borders-2021-5.jpg	Fluid Borders — Margaret Thatcher Projects, New York, 2021	4
33	1	/assets/installations/fluid-borders-2021-6.jpg	Fluid Borders — Margaret Thatcher Projects, New York, 2021	5
34	1	/assets/installations/fluid-borders-2021-7.jpg	Fluid Borders — Margaret Thatcher Projects, New York, 2021	6
\.


--
-- Data for Name: news; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.news (id, title, date, body, link, sort_order) FROM stdin;
\.


--
-- Data for Name: press; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.press (id, publication, title, year, image, pdf_url, quote, sort_order) FROM stdin;
10	Robischon Gallery	\N	\N	\N	\N	Geometric and organic elements build intricate compositions that beckon the viewer to take a closer look.	0
11	Fouladi Projects	\N	\N	\N	\N	A brush is never used. The dried acrylic forms become pliable building blocks — the basis of his paintings.	1
12	DeWitt Cheng · East Bay Express	\N	2010	\N	/assets/press/east-bay-express-2010.pdf	Insistently physical and overtly time-intensive — slow collaborations between maker and material.	2
13	Ringling College	\N	\N	\N	\N	Paint pouring on a separate surface that, once dried, migrates to the canvas in mosaic-like tiles — invoking concepts of the masses.	3
14	Arte al Límite	\N	2012	/assets/press/arte-al-limite-2012.jpg	\N		4
15	Art & Antiques — “Emerging Artists”	\N	2007	/assets/press/art-and-antiques-2007.jpg	\N		5
16	Miami University Young Painters Award	\N	2007	/assets/press/young-painters-2007.jpg	\N		6
17	Art in America — “Report from San Francisco I”	\N	2006	/assets/press/art-in-america-2006.jpg	\N		7
18	Artweek	\N	2005	/assets/press/artweek-2005.jpg	\N		8
\.


--
-- Data for Name: shows; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.shows (id, slug, title, gallery, city, year, blurb, press_url, sort_order, created_at, updated_at) FROM stdin;
1	fluid-borders	Fluid Borders	Margaret Thatcher Projects	New York	2021	Hand-cast acrylic drips, peeled and collaged — a brush is never used.	\N	0	2026-06-30 19:10:38.551429+00	2026-07-01 05:29:16.840881+00
2	variaciones-chuecas	Variaciones Chuecas	Robischon Gallery	Denver	2022	A solo survey of the mosaic-drip canvases.	\N	1	2026-06-30 19:10:38.563135+00	2026-07-01 05:29:16.942106+00
3	sin-seine	Sin Seine	Fouladi Projects	San Francisco	2023	Recent works on canvas and paper.	\N	2	2026-06-30 19:10:38.564047+00	2026-07-01 05:29:17.037328+00
4	adapt-applied-matter	Adapt · Applied Matter	Robischon Gallery	Denver	2020	Group exhibitions at Robischon Gallery.	\N	3	2026-06-30 19:10:38.564971+00	2026-07-01 05:29:17.038296+00
5	bacanales	Bacanales	Margaret Thatcher Projects	New York	2012	The early Bacanal series: tropical, operatic abstractions.	\N	4	2026-06-30 19:10:38.566403+00	2026-07-01 05:29:17.039374+00
12	nimba	NIMBA	Robischon Gallery	Denver	2024		\N	6	2026-07-01 05:29:17.137619+00	2026-07-01 05:29:17.137619+00
13	chromatic-echoes	Chromatic Echoes	Ringling College of Art and Design	Sarasota	2024		\N	7	2026-07-01 05:29:17.139165+00	2026-07-01 05:29:17.139165+00
14	chaotic-precisions	Chaotic Precisions	Margaret Thatcher Projects	New York	2024	With Gaston Bertin.	\N	8	2026-07-01 05:29:17.140321+00	2026-07-01 05:29:17.140321+00
15	cirio-totale	Cirio Totale	Margaret Thatcher Projects	New York	2023		\N	9	2026-07-01 05:29:17.141562+00	2026-07-01 05:29:17.141562+00
16	mesalinas-operaticas	Mesalinas Operáticas	Fouladi Projects	San Francisco	2020		\N	10	2026-07-01 05:29:17.142764+00	2026-07-01 05:29:17.142764+00
17	ohio-criollo	Ohio Criollo	Margaret Thatcher Projects	New York	2019		\N	11	2026-07-01 05:29:17.143745+00	2026-07-01 05:29:17.143745+00
18	las-mesalinas	Las Mesalinas y Otros Ensayos	Margaret Thatcher Projects	New York	2015		\N	12	2026-07-01 05:29:17.145109+00	2026-07-01 05:29:17.145109+00
19	stratigraphic	Stratigraphic	Chandra Cerrito Contemporary	Oakland	2010		\N	13	2026-07-01 05:29:17.146129+00	2026-07-01 05:29:17.146129+00
11	ostinatos	Ostinatos	Robischon Gallery	Denver	2026	\N	\N	5	2026-07-01 05:29:17.040456+00	2026-07-02 16:14:57.265195+00
\.


--
-- Data for Name: works; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.works (id, slug, title, year, medium, dimensions, image, status, surface, tier, show_id, sort_order, created_at, updated_at, is_hero) FROM stdin;
3	power-2023	Power	2023	Acrylic on paper	22.5 × 30 in	/assets/works/power-2023.jpg	Available	Paper	mediano	3	2	2026-06-30 19:10:38.655858+00	2026-07-01 05:29:17.340427+00	f
4	vergel-2023	Vergel	2023	Acrylic on paper	22 × 30 in	/assets/works/vergel-2023.jpg	Available	Paper	mediano	3	3	2026-06-30 19:10:38.656914+00	2026-07-01 05:29:17.34129+00	f
5	vesperal-2023	Vesperal	2023	Acrylic on paper	22.5 × 30 in	/assets/works/vesperal-2023.jpg	Available	Paper	mediano	3	4	2026-06-30 19:10:38.658218+00	2026-07-01 05:29:17.342142+00	f
6	cirio-ii-2022	Cirio II	2022	Acrylic on canvas	11.25 × 7.25 in	/assets/works/cirio-ii-2022.jpg	Available	Canvas	pequeno	3	5	2026-06-30 19:10:38.659245+00	2026-07-01 05:29:17.342724+00	f
7	bdpm-ni-2021	BDPM NI	2021	Acrylic on canvas	7.5 × 11.25 in	/assets/works/bdpm-ni-2021.jpg	Available	Canvas	pequeno	1	6	2026-06-30 19:10:38.660333+00	2026-07-01 05:29:17.438332+00	f
8	bdpm-nobsa-2021	BDPM Nobsa	2021	Acrylic on canvas	7.25 × 11.25 in	/assets/works/bdpm-nobsa-2021.jpg	Available	Canvas	pequeno	1	7	2026-06-30 19:10:38.661045+00	2026-07-01 05:29:17.439249+00	f
9	bdpm-vii-2021	BDPM VII	2021	Acrylic on canvas	7.25 × 11.25 in	/assets/works/bdpm-vii-2021.jpg	Available	Canvas	pequeno	1	8	2026-06-30 19:10:38.661696+00	2026-07-01 05:29:17.440507+00	f
10	chita-operatica-2021	Chita Operatica	2021	Acrylic on canvas	26 × 30 in	/assets/works/chita-operatica-2021.jpg	Available	Canvas	mediano	1	9	2026-06-30 19:10:38.662343+00	2026-07-01 05:29:17.441571+00	f
11	galactic-elemental-2021	Galactic Elemental	2021	Acrylic on canvas	11.25 × 7.5 in	/assets/works/galactic-elemental-2021.jpg	Available	Canvas	pequeno	1	10	2026-06-30 19:10:38.66309+00	2026-07-01 05:29:17.442808+00	f
12	mesalina-negra-2021	MESALINA NEGRA	2021	Acrylic on canvas	24 × 20 in	/assets/works/mesalina-negra-2021.jpg	Available	Canvas	mediano	4	11	2026-06-30 19:10:38.663874+00	2026-07-01 05:29:17.444589+00	f
13	magdalena-galactica-2021	Magdalena Galactica	2021	Acrylic on canvas	42 × 54 in	/assets/works/magdalena-galactica-2021.jpg	Available	Canvas	grande	1	12	2026-06-30 19:10:38.665508+00	2026-07-01 05:29:17.445854+00	f
14	molagavita-operatica-2021	Molagavita Operatica	2021	Acrylic on canvas	30 × 26 in	/assets/works/molagavita-operatica-2021.jpg	Available	Canvas	mediano	1	13	2026-06-30 19:10:38.753126+00	2026-07-01 05:29:17.447132+00	f
15	power-white-2021	POWER WHITE	2021	Acrylic on canvas	7.25 × 11.25 in	/assets/works/power-white-2021.jpg	Available	Canvas	pequeno	4	14	2026-06-30 19:10:38.754759+00	2026-07-01 05:29:17.447917+00	f
16	precusor-de-galacto-son-2021	Precusor de Galacto Son	2021	Acrylic on canvas	10.25 × 16 in	/assets/works/precusor-de-galacto-son-2021.jpg	Available	Canvas	pequeno	1	15	2026-06-30 19:10:38.756953+00	2026-07-01 05:29:17.448863+00	f
17	suprematist-blanco-mas-heyyy-2021	SUPREMATIST BLANCO MAS HEYYY	2021	Acrylic on canvas	30 × 26 in	/assets/works/suprematist-blanco-mas-heyyy-2021.jpg	Available	Canvas	mediano	4	16	2026-06-30 19:10:38.758358+00	2026-07-01 05:29:17.449497+00	f
18	snake-of-necklaces-2021	Snake of Necklaces	2021	Acrylic on canvas	54 × 42 in	/assets/works/snake-of-necklaces-2021.jpg	Available	Canvas	grande	1	17	2026-06-30 19:10:38.76007+00	2026-07-01 05:29:17.450106+00	f
19	sob-messalina-galactica-2021	Sob Messalina Galactica	2021	Acrylic on paper	30 × 22 in	/assets/works/sob-messalina-galactica-2021.jpg	Available	Paper	mediano	1	18	2026-06-30 19:10:38.76117+00	2026-07-01 05:29:17.451035+00	f
20	bdpm-ii-2020	BDPM II	2020	Acrylic on canvas	7.25 × 11.25 in	/assets/works/bdpm-ii-2020.jpg	Available	Canvas	pequeno	4	19	2026-06-30 19:10:38.762533+00	2026-07-01 05:29:17.537557+00	f
21	ensayo-v-2020	Ensayo V	2020	Acrylic on canvas	30 × 22 in	/assets/works/ensayo-v-2020.jpg	Available	Canvas	mediano	4	20	2026-06-30 19:10:38.763804+00	2026-07-01 05:29:17.539115+00	f
22	galactic-messalina-2020	GALACTIC MESSALINA	2020	Acrylic on canvas	30 × 26 in	/assets/works/galactic-messalina-2020.jpg	Available	Canvas	mediano	4	21	2026-06-30 19:10:38.764851+00	2026-07-01 05:29:17.541218+00	f
23	galactic-angelico-2020	Galactic Angelico	2020	Acrylic on paper	22 × 30 in	/assets/works/galactic-angelico-2020.jpg	Available	Paper	mediano	4	22	2026-06-30 19:10:38.85253+00	2026-07-01 05:29:17.636637+00	f
24	galactic-randi-ii-2020	Galactic Randi II	2020	Acrylic on paper	22 × 30 in	/assets/works/galactic-randi-ii-2020.jpg	Available	Paper	mediano	1	23	2026-06-30 19:10:38.853733+00	2026-07-01 05:29:17.638437+00	f
25	itiquilla-2020	ITIQUILLA	2020	Acrylic on paper	30 × 22 in	/assets/works/itiquilla-2020.jpg	Available	Paper	mediano	4	24	2026-06-30 19:10:38.855002+00	2026-07-01 05:29:17.640032+00	f
26	ich-operatica-2020	Ich Operatica	2020	Acrylic on canvas	30 × 26 in	/assets/works/ich-operatica-2020.jpg	Available	Canvas	mediano	1	25	2026-06-30 19:10:38.856344+00	2026-07-01 05:29:17.736963+00	f
27	jiri-2020	JIRI	2020	Acrylic on paper	22 × 30 in	/assets/works/jiri-2020.jpg	Available	Paper	mediano	4	26	2026-06-30 19:10:38.857226+00	2026-07-01 05:29:17.737897+00	f
28	pandemica-operatica-2020	Pandemica Operatica	2020	Acrylic on canvas	54 × 42 in	/assets/works/pandemica-operatica-2020.jpg	Available	Canvas	grande	4	27	2026-06-30 19:10:38.858093+00	2026-07-01 05:29:17.738506+00	f
29	v-venas-abiertas-2020	V (VENAS ABIERTAS)	2020	Acrylic on canvas	30 × 26 in	/assets/works/v-venas-abiertas-2020.jpg	Available	Canvas	mediano	4	28	2026-06-30 19:10:38.859155+00	2026-07-01 05:29:17.739216+00	f
30	variacion-de-bu-chueco-2020	VARIACION DE BU CHUECO	2020	Acrylic on paper	22 × 30 in	/assets/works/variacion-de-bu-chueco-2020.jpg	Available	Paper	mediano	4	29	2026-06-30 19:10:38.859954+00	2026-07-01 05:29:17.739894+00	f
31	bacanal-guerito-2011	Bacanal Guerito	2011	Acrylic on canvas	7.5 × 11.25 in	/assets/works/bacanal-guerito-2011.jpg	Available	Canvas	pequeno	5	30	2026-06-30 19:10:38.86082+00	2026-07-01 05:29:17.740686+00	f
32	bacanal-miuc-2011	Bacanal MIUC	2011	Acrylic on canvas	10 × 16 in	/assets/works/bacanal-miuc-2011.jpg	Available	Canvas	pequeno	5	31	2026-06-30 19:10:38.861896+00	2026-07-01 05:29:17.741226+00	f
33	bacanal-npi-2011	Bacanal NPI	2011	Acrylic on canvas	10 × 16 in	/assets/works/bacanal-npi-2011.jpg	Available	Canvas	pequeno	5	32	2026-06-30 19:10:38.862576+00	2026-07-01 05:29:17.742388+00	f
35	monitos-ccxv-2011	Monitos CCXV	2011	Acrylic on canvas	16 × 10 in	/assets/works/monitos-ccxv-2011.jpg	Available	Canvas	pequeno	5	34	2026-06-30 19:10:38.863941+00	2026-07-01 05:29:17.744947+00	f
36	surata-ccxviii-2011	Surata CCXVIII	2011	Acrylic on canvas	31 × 23 in	/assets/works/surata-ccxviii-2011.jpg	Available	Canvas	mediano	5	35	2026-06-30 19:10:38.952764+00	2026-07-01 05:29:17.74556+00	f
37	toribio-ccxvii-2011	Toribio CCXVII	2011	Acrylic on canvas	16 × 10 in	/assets/works/toribio-ccxvii-2011.jpg	Available	Canvas	pequeno	5	36	2026-06-30 19:10:38.954176+00	2026-07-01 05:29:17.746606+00	f
38	urbana-ccxx-2011	Urbana CCXX	2011	Acrylic on canvas	10 × 16 in	/assets/works/urbana-ccxx-2011.jpg	Available	Canvas	pequeno	5	37	2026-06-30 19:10:38.955215+00	2026-07-01 05:29:17.747806+00	f
39	zetaquira-ccxvi-2011	Zetaquira CCXVI	2011	Acrylic on canvas	10 × 16 in	/assets/works/zetaquira-ccxvi-2011.jpg	Available	Canvas	pequeno	5	38	2026-06-30 19:10:38.955984+00	2026-07-01 05:29:17.748385+00	f
40	untitled-painting-176-2008	Untitled Painting # 176	2008	Acrylic on canvas	11.25 × 7.5 in	/assets/works/untitled-painting-176-2008.jpg	\N	Canvas	pequeno	5	39	2026-06-30 19:10:38.956722+00	2026-07-01 13:35:45.835923+00	f
41	galactic-rand-variation-2020	GALACTIC RAND (Variation)	2020	Acrylic on canvas	10.25 × 16 in	/assets/works/galactic-rand-variation-na.jpg	Available	Canvas	pequeno	4	40	2026-06-30 19:10:38.957439+00	2026-07-01 05:29:17.839055+00	f
2	cirio-ii-2023	Cirio II	2023	Acrylic on canvas	11.25 × 7.25 in	/assets/works/cirio-ii-2023.jpg	\N	Canvas	pequeno	3	1	2026-06-30 19:10:38.654024+00	2026-07-01 13:34:30.939059+00	f
34	bacanal-requete-guero-2011	Bacanal Requete Guero	2011	Acrylic on canvas	10 × 16 in	/assets/works/bacanal-requete-guero-2011.jpg	Available	Canvas	pequeno	5	33	2026-06-30 19:10:38.863304+00	2026-07-01 05:29:17.74389+00	f
1	bdpm-ix-2023	BDPM IX	2023	Acrylic on canvas	7.25 × 11.5 in	/uploads/1783259636369-What-is-a-floor-plan-with-dimensions.png	\N	Canvas	pequeno	3	0	2026-06-30 19:10:38.567429+00	2026-07-05 13:53:57.983053+00	f
\.


--
-- Name: cv_entries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.cv_entries_id_seq', 31, true);


--
-- Name: installations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.installations_id_seq', 34, true);


--
-- Name: news_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.news_id_seq', 2, true);


--
-- Name: press_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.press_id_seq', 19, true);


--
-- Name: shows_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.shows_id_seq', 21, true);


--
-- Name: works_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.works_id_seq', 87, true);


--
-- Name: content content_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content
    ADD CONSTRAINT content_pkey PRIMARY KEY (key);


--
-- Name: cv_entries cv_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cv_entries
    ADD CONSTRAINT cv_entries_pkey PRIMARY KEY (id);


--
-- Name: installations installations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.installations
    ADD CONSTRAINT installations_pkey PRIMARY KEY (id);


--
-- Name: news news_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_pkey PRIMARY KEY (id);


--
-- Name: press press_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.press
    ADD CONSTRAINT press_pkey PRIMARY KEY (id);


--
-- Name: shows shows_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shows
    ADD CONSTRAINT shows_pkey PRIMARY KEY (id);


--
-- Name: shows shows_slug_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shows
    ADD CONSTRAINT shows_slug_key UNIQUE (slug);


--
-- Name: works works_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.works
    ADD CONSTRAINT works_pkey PRIMARY KEY (id);


--
-- Name: works works_slug_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.works
    ADD CONSTRAINT works_slug_key UNIQUE (slug);


--
-- Name: installations_show_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX installations_show_id_idx ON public.installations USING btree (show_id);


--
-- Name: works_show_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX works_show_id_idx ON public.works USING btree (show_id);


--
-- Name: installations installations_show_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.installations
    ADD CONSTRAINT installations_show_id_fkey FOREIGN KEY (show_id) REFERENCES public.shows(id) ON DELETE CASCADE;


--
-- Name: works works_show_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.works
    ADD CONSTRAINT works_show_id_fkey FOREIGN KEY (show_id) REFERENCES public.shows(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict FV540y1umrQSow0VulByIFO43SriVzUU9vs49iJdONU2jXMc75xwG3OMO3JL0KP

