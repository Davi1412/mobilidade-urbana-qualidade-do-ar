--
-- PostgreSQL database dump
--

\restrict plBb8t3basvTVLTTAQeUp2e6m6jX2H47GxEHmCqNveAd9lKtlpfSYr0t4USEEUW

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

-- Started on 2026-08-19 18:51:15

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

--
-- TOC entry 2 (class 3079 OID 16390)
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- TOC entry 5968 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- TOC entry 310 (class 1255 OID 17604)
-- Name: associar_coleta_estacao_proxima(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.associar_coleta_estacao_proxima() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_geom_coleta geometry(Point, 4326);
    v_id_estacao INTEGER;
    v_distancia_metros DOUBLE PRECISION;
BEGIN
    /*
     * Verifica se existem coordenadas suficientes
     * para realizar o cálculo espacial.
     */
    IF NEW.latitude IS NULL OR NEW.longitude IS NULL THEN
        RAISE NOTICE
            'Coleta % sem latitude ou longitude. Associação não realizada.',
            NEW.id;

        RETURN NEW;
    END IF;

    /*
     * Usa a geometria existente. Caso esteja nula,
     * cria um ponto com longitude e latitude.
     */
    v_geom_coleta := COALESCE(
        NEW.geom,
        ST_SetSRID(
            ST_MakePoint(
                NEW.longitude,
                NEW.latitude
            ),
            4326
        )
    );

    /*
     * Procura a estação mais próxima pertencente
     * à mesma região da linha.
     */
    SELECT
        e.id,
        ST_Distance(
            v_geom_coleta::geography,
            e.geom::geography
        )
    INTO
        v_id_estacao,
        v_distancia_metros
    FROM linha_onibus AS l

    JOIN estacao_qualidade_ar AS e
        ON e.id_regiao = l.id_regiao

    WHERE l.id = NEW.id_linha
      AND e.geom IS NOT NULL

    ORDER BY
        v_geom_coleta::geography
        <->
        e.geom::geography

    LIMIT 1;

    /*
     * Caso nenhuma estação seja encontrada,
     * informa o problema no console do PostgreSQL.
     */
    IF v_id_estacao IS NULL THEN
        RAISE NOTICE
            'Nenhuma estação encontrada para a coleta %, linha %.',
            NEW.id,
            NEW.id_linha;

        RETURN NEW;
    END IF;

    /*
     * Insere ou atualiza a associação espacial.
     */
    INSERT INTO veiculo_estacao_proxima (
        id_coleta,
        id_estacao,
        distancia_metros,
        data_calculo
    )
    VALUES (
        NEW.id,
        v_id_estacao,
        v_distancia_metros,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (id_coleta)
    DO UPDATE SET
        id_estacao = EXCLUDED.id_estacao,
        distancia_metros = EXCLUDED.distancia_metros,
        data_calculo = CURRENT_TIMESTAMP;

    RETURN NEW;

EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING
            'Erro ao associar a coleta %: %',
            NEW.id,
            SQLERRM;

        RETURN NEW;
END;
$$;



--
-- TOC entry 615 (class 1255 OID 17571)
-- Name: atualizar_geom_coleta(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.atualizar_geom_coleta() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.geom := ST_SetSRID(
        ST_MakePoint(NEW.longitude, NEW.latitude),
        4326
    );

    RETURN NEW;
END;
$$;



SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 234 (class 1259 OID 17537)
-- Name: coleta_posicao_veiculo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.coleta_posicao_veiculo (
    id integer NOT NULL,
    id_linha integer NOT NULL,
    prefixo_veiculo character varying(20),
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    janela_coleta character varying(20),
    data_hora_coleta timestamp without time zone NOT NULL,
    geom public.geometry(Point,4326)
);



--
-- TOC entry 233 (class 1259 OID 17536)
-- Name: coleta_posicao_veiculo_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.coleta_posicao_veiculo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- TOC entry 5969 (class 0 OID 0)
-- Dependencies: 233
-- Name: coleta_posicao_veiculo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.coleta_posicao_veiculo_id_seq OWNED BY public.coleta_posicao_veiculo.id;


--
-- TOC entry 228 (class 1259 OID 17490)
-- Name: estacao_qualidade_ar; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.estacao_qualidade_ar (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    id_regiao integer,
    geom public.geometry(Point,4326)
);



--
-- TOC entry 227 (class 1259 OID 17489)
-- Name: estacao_qualidade_ar_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.estacao_qualidade_ar_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- TOC entry 5970 (class 0 OID 0)
-- Dependencies: 227
-- Name: estacao_qualidade_ar_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.estacao_qualidade_ar_id_seq OWNED BY public.estacao_qualidade_ar.id;


--
-- TOC entry 232 (class 1259 OID 17523)
-- Name: linha_onibus; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.linha_onibus (
    id integer NOT NULL,
    codigo_linha character varying(20) NOT NULL,
    letreiro character varying(100),
    terminal_origem character varying(100),
    terminal_destino character varying(100),
    id_regiao integer,
    codigo_api character varying(20)
);



--
-- TOC entry 231 (class 1259 OID 17522)
-- Name: linha_onibus_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.linha_onibus_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- TOC entry 5971 (class 0 OID 0)
-- Dependencies: 231
-- Name: linha_onibus_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.linha_onibus_id_seq OWNED BY public.linha_onibus.id;


--
-- TOC entry 230 (class 1259 OID 17506)
-- Name: medicao_poluente; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.medicao_poluente (
    id integer NOT NULL,
    id_estacao integer NOT NULL,
    poluente character varying(20) NOT NULL,
    valor double precision NOT NULL,
    unidade character varying(20),
    data_hora timestamp without time zone NOT NULL
);



--
-- TOC entry 229 (class 1259 OID 17505)
-- Name: medicao_poluente_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.medicao_poluente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- TOC entry 5972 (class 0 OID 0)
-- Dependencies: 229
-- Name: medicao_poluente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.medicao_poluente_id_seq OWNED BY public.medicao_poluente.id;


--
-- TOC entry 226 (class 1259 OID 17479)
-- Name: regiao; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.regiao (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    geom public.geometry(Polygon,4326)
);



--
-- TOC entry 225 (class 1259 OID 17478)
-- Name: regiao_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.regiao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- TOC entry 5973 (class 0 OID 0)
-- Dependencies: 225
-- Name: regiao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.regiao_id_seq OWNED BY public.regiao.id;


--
-- TOC entry 236 (class 1259 OID 17574)
-- Name: veiculo_estacao_proxima; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.veiculo_estacao_proxima (
    id integer NOT NULL,
    id_coleta integer NOT NULL,
    id_estacao integer NOT NULL,
    distancia_metros double precision NOT NULL,
    data_calculo timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);



--
-- TOC entry 235 (class 1259 OID 17573)
-- Name: veiculo_estacao_proxima_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.veiculo_estacao_proxima_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- TOC entry 5974 (class 0 OID 0)
-- Dependencies: 235
-- Name: veiculo_estacao_proxima_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.veiculo_estacao_proxima_id_seq OWNED BY public.veiculo_estacao_proxima.id;


--
-- TOC entry 237 (class 1259 OID 17607)
-- Name: vw_coletas_enriquecidas; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_coletas_enriquecidas AS
 SELECT c.id AS id_coleta,
    c.prefixo_veiculo,
    l.codigo_linha,
    r.nome AS regiao,
    e.nome AS estacao,
    c.latitude,
    c.longitude,
    round((v.distancia_metros)::numeric, 2) AS distancia_metros,
        CASE
            WHEN (v.distancia_metros <= (1000)::double precision) THEN 'Até 1 km'::text
            WHEN (v.distancia_metros <= (3000)::double precision) THEN 'Entre 1 e 3 km'::text
            WHEN (v.distancia_metros <= (5000)::double precision) THEN 'Entre 3 e 5 km'::text
            WHEN (v.distancia_metros <= (10000)::double precision) THEN 'Entre 5 e 10 km'::text
            ELSE 'Acima de 10 km'::text
        END AS faixa_distancia,
    c.janela_coleta,
    c.data_hora_coleta,
    date(c.data_hora_coleta) AS data,
    EXTRACT(hour FROM c.data_hora_coleta) AS hora,
    v.data_calculo
   FROM ((((public.coleta_posicao_veiculo c
     JOIN public.linha_onibus l ON ((l.id = c.id_linha)))
     JOIN public.regiao r ON ((r.id = l.id_regiao)))
     LEFT JOIN public.veiculo_estacao_proxima v ON ((v.id_coleta = c.id)))
     LEFT JOIN public.estacao_qualidade_ar e ON ((e.id = v.id_estacao)));



--
-- TOC entry 243 (class 1259 OID 17632)
-- Name: vw_poluicao_horaria; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_poluicao_horaria AS
 SELECT e.id AS id_estacao,
    e.nome AS estacao,
    r.nome AS regiao,
    date_trunc('hour'::text, m.data_hora) AS data_hora_referencia,
    round((avg(
        CASE
            WHEN ((m.poluente)::text = 'MP10'::text) THEN m.valor
            ELSE NULL::double precision
        END))::numeric, 2) AS mp10,
    round((avg(
        CASE
            WHEN ((m.poluente)::text = 'MP2.5'::text) THEN m.valor
            ELSE NULL::double precision
        END))::numeric, 2) AS mp25,
    round((avg(
        CASE
            WHEN ((m.poluente)::text = 'NO'::text) THEN m.valor
            ELSE NULL::double precision
        END))::numeric, 2) AS no,
    round((avg(
        CASE
            WHEN ((m.poluente)::text = 'NO2'::text) THEN m.valor
            ELSE NULL::double precision
        END))::numeric, 2) AS no2
   FROM ((public.medicao_poluente m
     JOIN public.estacao_qualidade_ar e ON ((e.id = m.id_estacao)))
     JOIN public.regiao r ON ((r.id = e.id_regiao)))
  GROUP BY e.id, e.nome, r.nome, (date_trunc('hour'::text, m.data_hora))
  ORDER BY (date_trunc('hour'::text, m.data_hora)), e.nome;



--
-- TOC entry 244 (class 1259 OID 17637)
-- Name: vw_fato_mobilidade_poluicao; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_fato_mobilidade_poluicao AS
 SELECT c.id_coleta,
    c.prefixo_veiculo,
    c.codigo_linha,
    c.regiao,
    c.estacao,
    c.latitude,
    c.longitude,
    c.distancia_metros,
    c.faixa_distancia,
    c.janela_coleta,
    c.data_hora_coleta,
    date_trunc('hour'::text, c.data_hora_coleta) AS hora_referencia,
    p.mp10,
    p.mp25,
    p.no,
    p.no2
   FROM (public.vw_coletas_enriquecidas c
     LEFT JOIN public.vw_poluicao_horaria p ON ((((p.estacao)::text = (c.estacao)::text) AND (p.data_hora_referencia = date_trunc('hour'::text, c.data_hora_coleta)))));



--
-- TOC entry 248 (class 1259 OID 17656)
-- Name: vw_dashboard_distancias; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_dashboard_distancias AS
 SELECT faixa_distancia,
    count(*) AS total_coletas,
    round((((count(*))::numeric / NULLIF(sum(count(*)) OVER (), (0)::numeric)) * (100)::numeric), 2) AS percentual
   FROM public.vw_fato_mobilidade_poluicao
  GROUP BY faixa_distancia
  ORDER BY
        CASE faixa_distancia
            WHEN 'Até 1 km'::text THEN 1
            WHEN '1 a 3 km'::text THEN 2
            WHEN '3 a 5 km'::text THEN 3
            WHEN '5 a 10 km'::text THEN 4
            WHEN 'Acima de 10 km'::text THEN 5
            ELSE 6
        END;



--
-- TOC entry 245 (class 1259 OID 17642)
-- Name: vw_dashboard_executivo; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_dashboard_executivo AS
 SELECT count(*) AS total_posicoes,
    count(DISTINCT prefixo_veiculo) AS total_veiculos,
    count(DISTINCT codigo_linha) AS total_linhas,
    count(DISTINCT regiao) AS total_regioes,
    round(avg(distancia_metros), 2) AS distancia_media,
    round(max(distancia_metros), 2) AS maior_distancia,
    count(mp10) AS registros_com_mp10,
    count(mp25) AS registros_com_mp25,
    count(no) AS registros_com_no,
    count(no2) AS registros_com_no2,
    round((((count(mp25))::numeric / (NULLIF(count(*), 0))::numeric) * (100)::numeric), 2) AS cobertura_ambiental_percentual
   FROM public.vw_fato_mobilidade_poluicao;



--
-- TOC entry 247 (class 1259 OID 17652)
-- Name: vw_dashboard_fluxo_linha; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_dashboard_fluxo_linha AS
 SELECT codigo_linha,
    count(*) AS total_coletas,
    count(DISTINCT prefixo_veiculo) AS total_veiculos,
    round(avg(distancia_metros), 2) AS distancia_media
   FROM public.vw_fato_mobilidade_poluicao
  GROUP BY codigo_linha
  ORDER BY (count(*)) DESC;



--
-- TOC entry 242 (class 1259 OID 17628)
-- Name: vw_distribuicao_distancias; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_distribuicao_distancias AS
 SELECT faixa_distancia,
    count(*) AS total_posicoes,
    round((((count(*))::numeric / sum(count(*)) OVER ()) * (100)::numeric), 2) AS percentual
   FROM public.vw_coletas_enriquecidas
  GROUP BY faixa_distancia
  ORDER BY faixa_distancia;



--
-- TOC entry 241 (class 1259 OID 17624)
-- Name: vw_fluxo_horario; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_fluxo_horario AS
 SELECT hora,
    count(*) AS total_posicoes,
    count(DISTINCT prefixo_veiculo) AS total_veiculos
   FROM public.vw_coletas_enriquecidas
  GROUP BY hora
  ORDER BY hora;



--
-- TOC entry 240 (class 1259 OID 17620)
-- Name: vw_fluxo_por_linha; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_fluxo_por_linha AS
 SELECT codigo_linha,
    regiao,
    count(*) AS total_posicoes,
    count(DISTINCT prefixo_veiculo) AS total_veiculos,
    round(avg(distancia_metros), 2) AS distancia_media
   FROM public.vw_coletas_enriquecidas
  GROUP BY codigo_linha, regiao
  ORDER BY (count(*)) DESC;



--
-- TOC entry 246 (class 1259 OID 17647)
-- Name: vw_insights_dashboard; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_insights_dashboard AS
 WITH fluxo_regiao AS (
         SELECT vw_fato_mobilidade_poluicao.regiao,
            count(*) AS total_coletas,
            row_number() OVER (ORDER BY (count(*)) DESC, vw_fato_mobilidade_poluicao.regiao) AS posicao
           FROM public.vw_fato_mobilidade_poluicao
          GROUP BY vw_fato_mobilidade_poluicao.regiao
        ), fluxo_linha AS (
         SELECT vw_fato_mobilidade_poluicao.codigo_linha,
            count(*) AS total_coletas,
            row_number() OVER (ORDER BY (count(*)) DESC, vw_fato_mobilidade_poluicao.codigo_linha) AS posicao
           FROM public.vw_fato_mobilidade_poluicao
          GROUP BY vw_fato_mobilidade_poluicao.codigo_linha
        ), fluxo_estacao AS (
         SELECT vw_fato_mobilidade_poluicao.estacao,
            count(*) AS total_coletas,
            row_number() OVER (ORDER BY (count(*)) DESC, vw_fato_mobilidade_poluicao.estacao) AS posicao
           FROM public.vw_fato_mobilidade_poluicao
          GROUP BY vw_fato_mobilidade_poluicao.estacao
        )
 SELECT ( SELECT fluxo_regiao.regiao
           FROM fluxo_regiao
          WHERE (fluxo_regiao.posicao = 1)) AS regiao_maior_fluxo,
    ( SELECT fluxo_regiao.total_coletas
           FROM fluxo_regiao
          WHERE (fluxo_regiao.posicao = 1)) AS total_regiao_maior_fluxo,
    ( SELECT fluxo_linha.codigo_linha
           FROM fluxo_linha
          WHERE (fluxo_linha.posicao = 1)) AS linha_mais_observada,
    ( SELECT fluxo_linha.total_coletas
           FROM fluxo_linha
          WHERE (fluxo_linha.posicao = 1)) AS total_linha_mais_observada,
    ( SELECT fluxo_estacao.estacao
           FROM fluxo_estacao
          WHERE (fluxo_estacao.posicao = 1)) AS estacao_mais_utilizada,
    ( SELECT fluxo_estacao.total_coletas
           FROM fluxo_estacao
          WHERE (fluxo_estacao.posicao = 1)) AS total_estacao_mais_utilizada;



--
-- TOC entry 239 (class 1259 OID 17616)
-- Name: vw_kpis_dashboard; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_kpis_dashboard AS
 SELECT count(*) AS total_posicoes,
    count(DISTINCT prefixo_veiculo) AS total_veiculos,
    count(DISTINCT codigo_linha) AS total_linhas,
    count(DISTINCT regiao) AS total_regioes,
    round(avg(distancia_metros), 2) AS distancia_media_m,
    round(min(distancia_metros), 2) AS menor_distancia,
    round(max(distancia_metros), 2) AS maior_distancia
   FROM public.vw_coletas_enriquecidas;



--
-- TOC entry 238 (class 1259 OID 17612)
-- Name: vw_mobilidade_por_regiao; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_mobilidade_por_regiao AS
 SELECT regiao,
    count(*) AS total_posicoes,
    count(DISTINCT codigo_linha) AS total_linhas,
    count(DISTINCT prefixo_veiculo) AS total_veiculos,
    round(avg(distancia_metros), 2) AS distancia_media_m,
    round(min(distancia_metros), 2) AS menor_distancia_m,
    round(max(distancia_metros), 2) AS maior_distancia_m
   FROM public.vw_coletas_enriquecidas
  GROUP BY regiao
  ORDER BY regiao;



--
-- TOC entry 5747 (class 2604 OID 17540)
-- Name: coleta_posicao_veiculo id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.coleta_posicao_veiculo ALTER COLUMN id SET DEFAULT nextval('public.coleta_posicao_veiculo_id_seq'::regclass);


--
-- TOC entry 5744 (class 2604 OID 17493)
-- Name: estacao_qualidade_ar id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.estacao_qualidade_ar ALTER COLUMN id SET DEFAULT nextval('public.estacao_qualidade_ar_id_seq'::regclass);


--
-- TOC entry 5746 (class 2604 OID 17526)
-- Name: linha_onibus id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.linha_onibus ALTER COLUMN id SET DEFAULT nextval('public.linha_onibus_id_seq'::regclass);


--
-- TOC entry 5745 (class 2604 OID 17509)
-- Name: medicao_poluente id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medicao_poluente ALTER COLUMN id SET DEFAULT nextval('public.medicao_poluente_id_seq'::regclass);


--
-- TOC entry 5743 (class 2604 OID 17482)
-- Name: regiao id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.regiao ALTER COLUMN id SET DEFAULT nextval('public.regiao_id_seq'::regclass);


--
-- TOC entry 5748 (class 2604 OID 17577)
-- Name: veiculo_estacao_proxima id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.veiculo_estacao_proxima ALTER COLUMN id SET DEFAULT nextval('public.veiculo_estacao_proxima_id_seq'::regclass);


--
-- TOC entry 5960 (class 0 OID 17537)
-- Dependencies: 234
-- Data for Name: coleta_posicao_veiculo; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5954 (class 0 OID 17490)
-- Dependencies: 228
-- Data for Name: estacao_qualidade_ar; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5958 (class 0 OID 17523)
-- Dependencies: 232
-- Data for Name: linha_onibus; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5956 (class 0 OID 17506)
-- Dependencies: 230
-- Data for Name: medicao_poluente; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5952 (class 0 OID 17479)
-- Dependencies: 226
-- Data for Name: regiao; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5742 (class 0 OID 16709)
-- Dependencies: 221
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5962 (class 0 OID 17574)
-- Dependencies: 236
-- Data for Name: veiculo_estacao_proxima; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5975 (class 0 OID 0)
-- Dependencies: 233
-- Name: coleta_posicao_veiculo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--



--
-- TOC entry 5976 (class 0 OID 0)
-- Dependencies: 227
-- Name: estacao_qualidade_ar_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--



--
-- TOC entry 5977 (class 0 OID 0)
-- Dependencies: 231
-- Name: linha_onibus_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--



--
-- TOC entry 5978 (class 0 OID 0)
-- Dependencies: 229
-- Name: medicao_poluente_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--



--
-- TOC entry 5979 (class 0 OID 0)
-- Dependencies: 225
-- Name: regiao_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--



--
-- TOC entry 5980 (class 0 OID 0)
-- Dependencies: 235
-- Name: veiculo_estacao_proxima_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--



--
-- TOC entry 5768 (class 2606 OID 17547)
-- Name: coleta_posicao_veiculo coleta_posicao_veiculo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.coleta_posicao_veiculo
    ADD CONSTRAINT coleta_posicao_veiculo_pkey PRIMARY KEY (id);


--
-- TOC entry 5756 (class 2606 OID 17499)
-- Name: estacao_qualidade_ar estacao_qualidade_ar_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.estacao_qualidade_ar
    ADD CONSTRAINT estacao_qualidade_ar_pkey PRIMARY KEY (id);


--
-- TOC entry 5764 (class 2606 OID 17530)
-- Name: linha_onibus linha_onibus_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.linha_onibus
    ADD CONSTRAINT linha_onibus_pkey PRIMARY KEY (id);


--
-- TOC entry 5766 (class 2606 OID 17558)
-- Name: linha_onibus linha_unica; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.linha_onibus
    ADD CONSTRAINT linha_unica UNIQUE (codigo_linha, letreiro, terminal_origem);


--
-- TOC entry 5760 (class 2606 OID 17516)
-- Name: medicao_poluente medicao_poluente_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medicao_poluente
    ADD CONSTRAINT medicao_poluente_pkey PRIMARY KEY (id);


--
-- TOC entry 5762 (class 2606 OID 17564)
-- Name: medicao_poluente medicao_unica; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medicao_poluente
    ADD CONSTRAINT medicao_unica UNIQUE (id_estacao, poluente, data_hora);


--
-- TOC entry 5754 (class 2606 OID 17488)
-- Name: regiao regiao_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.regiao
    ADD CONSTRAINT regiao_pkey PRIMARY KEY (id);


--
-- TOC entry 5776 (class 2606 OID 17598)
-- Name: veiculo_estacao_proxima veiculo_estacao_coleta_unica; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.veiculo_estacao_proxima
    ADD CONSTRAINT veiculo_estacao_coleta_unica UNIQUE (id_coleta);


--
-- TOC entry 5778 (class 2606 OID 17584)
-- Name: veiculo_estacao_proxima veiculo_estacao_proxima_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.veiculo_estacao_proxima
    ADD CONSTRAINT veiculo_estacao_proxima_pkey PRIMARY KEY (id);


--
-- TOC entry 5771 (class 1259 OID 17595)
-- Name: idx_associacao_coleta; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_associacao_coleta ON public.veiculo_estacao_proxima USING btree (id_coleta);


--
-- TOC entry 5772 (class 1259 OID 17596)
-- Name: idx_associacao_estacao; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_associacao_estacao ON public.veiculo_estacao_proxima USING btree (id_estacao);


--
-- TOC entry 5769 (class 1259 OID 17554)
-- Name: idx_coleta_data; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_coleta_data ON public.coleta_posicao_veiculo USING btree (data_hora_coleta);


--
-- TOC entry 5770 (class 1259 OID 17570)
-- Name: idx_coleta_geom; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_coleta_geom ON public.coleta_posicao_veiculo USING gist (geom);


--
-- TOC entry 5757 (class 1259 OID 17569)
-- Name: idx_estacao_geom; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_estacao_geom ON public.estacao_qualidade_ar USING gist (geom);


--
-- TOC entry 5758 (class 1259 OID 17553)
-- Name: idx_medicao_data; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_medicao_data ON public.medicao_poluente USING btree (data_hora);


--
-- TOC entry 5773 (class 1259 OID 17603)
-- Name: idx_veiculo_estacao_distancia; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_veiculo_estacao_distancia ON public.veiculo_estacao_proxima USING btree (distancia_metros);


--
-- TOC entry 5774 (class 1259 OID 17602)
-- Name: idx_veiculo_estacao_id_estacao; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_veiculo_estacao_id_estacao ON public.veiculo_estacao_proxima USING btree (id_estacao);


--
-- TOC entry 5785 (class 2620 OID 17606)
-- Name: coleta_posicao_veiculo trg_associar_coleta_estacao_proxima; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_associar_coleta_estacao_proxima AFTER INSERT OR UPDATE OF geom, latitude, longitude, id_linha ON public.coleta_posicao_veiculo FOR EACH ROW WHEN (((new.latitude IS NOT NULL) AND (new.longitude IS NOT NULL))) EXECUTE FUNCTION public.associar_coleta_estacao_proxima();


--
-- TOC entry 5786 (class 2620 OID 17572)
-- Name: coleta_posicao_veiculo trg_atualizar_geom_coleta; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_atualizar_geom_coleta BEFORE INSERT OR UPDATE OF latitude, longitude ON public.coleta_posicao_veiculo FOR EACH ROW EXECUTE FUNCTION public.atualizar_geom_coleta();


--
-- TOC entry 5782 (class 2606 OID 17548)
-- Name: coleta_posicao_veiculo coleta_posicao_veiculo_id_linha_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.coleta_posicao_veiculo
    ADD CONSTRAINT coleta_posicao_veiculo_id_linha_fkey FOREIGN KEY (id_linha) REFERENCES public.linha_onibus(id);


--
-- TOC entry 5779 (class 2606 OID 17500)
-- Name: estacao_qualidade_ar estacao_qualidade_ar_id_regiao_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.estacao_qualidade_ar
    ADD CONSTRAINT estacao_qualidade_ar_id_regiao_fkey FOREIGN KEY (id_regiao) REFERENCES public.regiao(id);


--
-- TOC entry 5783 (class 2606 OID 17585)
-- Name: veiculo_estacao_proxima fk_coleta; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.veiculo_estacao_proxima
    ADD CONSTRAINT fk_coleta FOREIGN KEY (id_coleta) REFERENCES public.coleta_posicao_veiculo(id);


--
-- TOC entry 5784 (class 2606 OID 17590)
-- Name: veiculo_estacao_proxima fk_estacao; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.veiculo_estacao_proxima
    ADD CONSTRAINT fk_estacao FOREIGN KEY (id_estacao) REFERENCES public.estacao_qualidade_ar(id);


--
-- TOC entry 5781 (class 2606 OID 17531)
-- Name: linha_onibus linha_onibus_id_regiao_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.linha_onibus
    ADD CONSTRAINT linha_onibus_id_regiao_fkey FOREIGN KEY (id_regiao) REFERENCES public.regiao(id);


--
-- TOC entry 5780 (class 2606 OID 17517)
-- Name: medicao_poluente medicao_poluente_id_estacao_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medicao_poluente
    ADD CONSTRAINT medicao_poluente_id_estacao_fkey FOREIGN KEY (id_estacao) REFERENCES public.estacao_qualidade_ar(id);


-- Completed on 2026-08-19 18:51:15

--
-- PostgreSQL database dump complete
--

\unrestrict plBb8t3basvTVLTTAQeUp2e6m6jX2H47GxEHmCqNveAd9lKtlpfSYr0t4USEEUW

