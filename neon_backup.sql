--
-- PostgreSQL database dump
--

\restrict 5rVlTucyhOme78N2DgmmL4EfpKZJo566L4cbmWAsN5B9BQplZAaZqOhVgIaAdiz

-- Dumped from database version 17.5 (6bc9ef8)
-- Dumped by pg_dump version 17.6 (Debian 17.6-2.pgdg13+1)

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
-- Name: coupontype; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.coupontype AS ENUM (
    'FIXED',
    'PERCENTAGE',
    'FREE_SHIPPING'
);


ALTER TYPE public.coupontype OWNER TO neondb_owner;

--
-- Name: orderitemtype; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.orderitemtype AS ENUM (
    'SIMPLE',
    'VARIABLE',
    'GROUPED'
);


ALTER TYPE public.orderitemtype OWNER TO neondb_owner;

--
-- Name: paymentmethod; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.paymentmethod AS ENUM (
    'BANK_TRANSFER',
    'CASH',
    'DIGITAL_WALLET'
);


ALTER TYPE public.paymentmethod OWNER TO neondb_owner;

--
-- Name: productstatus; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.productstatus AS ENUM (
    'PUBLISH',
    'DRAFT'
);


ALTER TYPE public.productstatus OWNER TO neondb_owner;

--
-- Name: producttype; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.producttype AS ENUM (
    'SIMPLE',
    'VARIABLE',
    'GROUPED'
);


ALTER TYPE public.producttype OWNER TO neondb_owner;

--
-- Name: purchasetype; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.purchasetype AS ENUM (
    'DEBIT',
    'CREDIT'
);


ALTER TYPE public.purchasetype OWNER TO neondb_owner;

--
-- Name: refundstatus; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.refundstatus AS ENUM (
    'PENDING',
    'PROCESSED',
    'FAILED'
);


ALTER TYPE public.refundstatus OWNER TO neondb_owner;

--
-- Name: returnstatus; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.returnstatus AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'COMPLETED'
);


ALTER TYPE public.returnstatus OWNER TO neondb_owner;

--
-- Name: returntype; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.returntype AS ENUM (
    'FULL_ORDER',
    'SINGLE_PRODUCT'
);


ALTER TYPE public.returntype OWNER TO neondb_owner;

--
-- Name: role; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.role AS ENUM (
    'master',
    'admin',
    'user'
);


ALTER TYPE public.role OWNER TO neondb_owner;

--
-- Name: shippingtype; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.shippingtype AS ENUM (
    'FIXED',
    'PERCENTAGE',
    'FREE_SHIPPING'
);


ALTER TYPE public.shippingtype OWNER TO neondb_owner;

--
-- Name: transactiontype; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.transactiontype AS ENUM (
    'PURCHASE',
    'STOCK_ADDITION',
    'STOCK_ADJUSTMENT',
    'RETURN',
    'DAMAGE',
    'TRANSFER'
);


ALTER TYPE public.transactiontype OWNER TO neondb_owner;

--
-- Name: withdrawstatus; Type: TYPE; Schema: public; Owner: neondb_owner
--

CREATE TYPE public.withdrawstatus AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'PROCESSED',
    'FAILED'
);


ALTER TYPE public.withdrawstatus OWNER TO neondb_owner;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: address; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.address (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    title character varying(191) NOT NULL,
    type character varying(191) NOT NULL,
    is_default boolean NOT NULL,
    address json,
    location json,
    customer_id integer NOT NULL
);


ALTER TABLE public.address OWNER TO neondb_owner;

--
-- Name: address_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.address_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.address_id_seq OWNER TO neondb_owner;

--
-- Name: address_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.address_id_seq OWNED BY public.address.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO neondb_owner;

--
-- Name: attribute_product; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.attribute_product (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    attribute_value_id integer NOT NULL,
    product_id integer NOT NULL
);


ALTER TABLE public.attribute_product OWNER TO neondb_owner;

--
-- Name: attribute_product_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.attribute_product_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attribute_product_id_seq OWNER TO neondb_owner;

--
-- Name: attribute_product_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.attribute_product_id_seq OWNED BY public.attribute_product.id;


--
-- Name: attribute_values; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.attribute_values (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    slug character varying(191) NOT NULL,
    attribute_id integer NOT NULL,
    value character varying(191) NOT NULL,
    language character varying(191) NOT NULL,
    meta character varying(191)
);


ALTER TABLE public.attribute_values OWNER TO neondb_owner;

--
-- Name: attribute_values_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.attribute_values_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attribute_values_id_seq OWNER TO neondb_owner;

--
-- Name: attribute_values_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.attribute_values_id_seq OWNED BY public.attribute_values.id;


--
-- Name: attributes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.attributes (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    slug character varying(191) NOT NULL,
    language character varying(191) NOT NULL,
    name character varying(191) NOT NULL
);


ALTER TABLE public.attributes OWNER TO neondb_owner;

--
-- Name: attributes_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.attributes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attributes_id_seq OWNER TO neondb_owner;

--
-- Name: attributes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.attributes_id_seq OWNED BY public.attributes.id;


--
-- Name: banners; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.banners (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    category_id integer,
    name character varying(191) NOT NULL,
    slug character varying(191) NOT NULL,
    language character varying(191) NOT NULL,
    description character varying,
    is_active boolean NOT NULL,
    image json
);


ALTER TABLE public.banners OWNER TO neondb_owner;

--
-- Name: banners_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.banners_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.banners_id_seq OWNER TO neondb_owner;

--
-- Name: banners_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.banners_id_seq OWNED BY public.banners.id;


--
-- Name: carts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.carts (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    product_id integer NOT NULL,
    user_id integer NOT NULL,
    shop_id integer NOT NULL,
    quantity integer NOT NULL
);


ALTER TABLE public.carts OWNER TO neondb_owner;

--
-- Name: carts_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.carts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.carts_id_seq OWNER TO neondb_owner;

--
-- Name: carts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.carts_id_seq OWNED BY public.carts.id;


--
-- Name: categories; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.categories (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    parent_id integer,
    name character varying(191) NOT NULL,
    slug character varying(191) NOT NULL,
    level integer NOT NULL,
    language character varying(191) NOT NULL,
    icon character varying(191),
    image json,
    details character varying,
    admin_commission_rate double precision,
    is_active boolean NOT NULL,
    deleted_at timestamp without time zone,
    root_id integer,
    seo_description character varying,
    seo_keywords character varying,
    seo_title character varying
);


ALTER TABLE public.categories OWNER TO neondb_owner;

--
-- Name: categories_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.categories_id_seq OWNER TO neondb_owner;

--
-- Name: categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.categories_id_seq OWNED BY public.categories.id;


--
-- Name: coupons; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.coupons (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    code character varying(191) NOT NULL,
    language character varying(10) NOT NULL,
    description character varying,
    image json,
    type public.coupontype NOT NULL,
    amount double precision NOT NULL,
    minimum_cart_amount double precision NOT NULL,
    active_from timestamp without time zone NOT NULL,
    expire_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.coupons OWNER TO neondb_owner;

--
-- Name: coupons_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.coupons_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.coupons_id_seq OWNER TO neondb_owner;

--
-- Name: coupons_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.coupons_id_seq OWNED BY public.coupons.id;


--
-- Name: email_template; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.email_template (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    name character varying(191) NOT NULL,
    slug character varying(191) NOT NULL,
    subject character varying(300) NOT NULL,
    content jsonb,
    is_active boolean NOT NULL,
    language character varying(191) NOT NULL,
    html_content character varying
);


ALTER TABLE public.email_template OWNER TO neondb_owner;

--
-- Name: email_template_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.email_template_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.email_template_id_seq OWNER TO neondb_owner;

--
-- Name: email_template_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.email_template_id_seq OWNED BY public.email_template.id;


--
-- Name: faqs; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.faqs (
    id integer NOT NULL,
    question character varying,
    answer character varying,
    "order" integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone
);


ALTER TABLE public.faqs OWNER TO neondb_owner;

--
-- Name: faqs_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.faqs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.faqs_id_seq OWNER TO neondb_owner;

--
-- Name: faqs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.faqs_id_seq OWNED BY public.faqs.id;


--
-- Name: manufacturers; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.manufacturers (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    name character varying(191) NOT NULL,
    is_approved boolean NOT NULL,
    image json,
    cover_image json,
    slug character varying(191) NOT NULL,
    language character varying(191) NOT NULL,
    description character varying,
    website character varying(191),
    socials json,
    is_active boolean NOT NULL
);


ALTER TABLE public.manufacturers OWNER TO neondb_owner;

--
-- Name: manufacturers_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.manufacturers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.manufacturers_id_seq OWNER TO neondb_owner;

--
-- Name: manufacturers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.manufacturers_id_seq OWNED BY public.manufacturers.id;


--
-- Name: media; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.media (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    user_id integer NOT NULL,
    media_type character varying NOT NULL,
    filename character varying NOT NULL,
    extension character varying NOT NULL,
    original character varying NOT NULL,
    size_mb double precision,
    thumbnail character varying
);


ALTER TABLE public.media OWNER TO neondb_owner;

--
-- Name: media_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.media_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.media_id_seq OWNER TO neondb_owner;

--
-- Name: media_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.media_id_seq OWNED BY public.media.id;


--
-- Name: order_product; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.order_product (
    id integer NOT NULL,
    order_id integer NOT NULL,
    product_id integer NOT NULL,
    variation_option_id integer,
    order_quantity character varying(191) NOT NULL,
    unit_price double precision NOT NULL,
    subtotal double precision NOT NULL,
    admin_commission numeric(10,2) DEFAULT 0.00 NOT NULL,
    deleted_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    item_type public.orderitemtype NOT NULL,
    variation_data jsonb,
    variation_snapshot jsonb,
    shop_id integer
);


ALTER TABLE public.order_product OWNER TO neondb_owner;

--
-- Name: order_product_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.order_product_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.order_product_id_seq OWNER TO neondb_owner;

--
-- Name: order_product_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.order_product_id_seq OWNED BY public.order_product.id;


--
-- Name: orders; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.orders (
    id integer NOT NULL,
    tracking_number character varying(191) NOT NULL,
    customer_id integer,
    customer_contact character varying(191) NOT NULL,
    customer_name character varying(191),
    amount double precision NOT NULL,
    sales_tax double precision,
    paid_total double precision,
    total double precision,
    cancelled_amount numeric(10,2) DEFAULT 0.00 NOT NULL,
    admin_commission_amount numeric(10,2) DEFAULT 0.00 NOT NULL,
    language character varying(191) DEFAULT 'en'::character varying NOT NULL,
    coupon_id integer,
    discount double precision,
    payment_gateway character varying(191),
    shipping_address json,
    billing_address json,
    logistics_provider integer,
    delivery_fee double precision,
    delivery_time character varying(191),
    fullfillment_id integer,
    assign_date timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    order_status character varying,
    payment_status character varying
);


ALTER TABLE public.orders OWNER TO neondb_owner;

--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.orders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.orders_id_seq OWNER TO neondb_owner;

--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.orders_id_seq OWNED BY public.orders.id;


--
-- Name: orders_status; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.orders_status (
    id integer NOT NULL,
    order_id integer NOT NULL,
    language character varying(191) DEFAULT 'en'::character varying NOT NULL,
    order_pending_date timestamp without time zone,
    order_processing_date timestamp without time zone,
    order_completed_date timestamp without time zone,
    order_refunded_date timestamp without time zone,
    order_failed_date timestamp without time zone,
    order_cancelled_date timestamp without time zone,
    order_at_local_facility_date timestamp without time zone,
    order_out_for_delivery_date timestamp without time zone,
    order_packed_date timestamp without time zone,
    order_at_distribution_center_date timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone
);


ALTER TABLE public.orders_status OWNER TO neondb_owner;

--
-- Name: orders_status_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.orders_status_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.orders_status_id_seq OWNER TO neondb_owner;

--
-- Name: orders_status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.orders_status_id_seq OWNED BY public.orders_status.id;


--
-- Name: product_import_history; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.product_import_history (
    id integer NOT NULL,
    filename character varying NOT NULL,
    original_filename character varying NOT NULL,
    file_size integer NOT NULL,
    total_records integer NOT NULL,
    successful_records integer NOT NULL,
    failed_records integer NOT NULL,
    status character varying NOT NULL,
    import_errors json,
    imported_products json,
    shop_id integer NOT NULL,
    imported_by integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    completed_at timestamp without time zone
);


ALTER TABLE public.product_import_history OWNER TO neondb_owner;

--
-- Name: product_import_history_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.product_import_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.product_import_history_id_seq OWNER TO neondb_owner;

--
-- Name: product_import_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.product_import_history_id_seq OWNED BY public.product_import_history.id;


--
-- Name: product_purchase; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.product_purchase (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    product_id integer,
    variation_option_id integer,
    quantity integer NOT NULL,
    purchase_date timestamp without time zone NOT NULL,
    price double precision,
    sale_price double precision,
    purchase_price double precision NOT NULL,
    shop_id integer NOT NULL,
    min_price double precision,
    max_price double precision,
    purchase_type public.purchasetype NOT NULL,
    transaction_type public.transactiontype NOT NULL,
    reference_number character varying(191),
    supplier_name character varying(191),
    invoice_number character varying(191),
    batch_number character varying(191),
    expiry_date timestamp without time zone,
    notes character varying,
    added_by integer NOT NULL,
    previous_stock integer NOT NULL,
    new_stock integer NOT NULL,
    transaction_details json
);


ALTER TABLE public.product_purchase OWNER TO neondb_owner;

--
-- Name: product_purchase_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.product_purchase_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.product_purchase_id_seq OWNER TO neondb_owner;

--
-- Name: product_purchase_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.product_purchase_id_seq OWNED BY public.product_purchase.id;


--
-- Name: product_purchase_variation_options; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.product_purchase_variation_options (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    product_purchase_id integer NOT NULL,
    variation_options_id integer,
    price double precision NOT NULL,
    sale_price double precision,
    purchase_price double precision,
    language character varying(191) NOT NULL,
    quantity integer NOT NULL,
    sku character varying(191),
    product_id integer,
    purchase_date timestamp without time zone
);


ALTER TABLE public.product_purchase_variation_options OWNER TO neondb_owner;

--
-- Name: product_purchase_variation_options_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.product_purchase_variation_options_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.product_purchase_variation_options_id_seq OWNER TO neondb_owner;

--
-- Name: product_purchase_variation_options_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.product_purchase_variation_options_id_seq OWNED BY public.product_purchase_variation_options.id;


--
-- Name: products; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.products (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    name character varying(191) NOT NULL,
    slug character varying(191) NOT NULL,
    description character varying,
    price double precision,
    is_active boolean DEFAULT true NOT NULL,
    sale_price double precision,
    purchase_price double precision,
    language character varying(191) NOT NULL,
    min_price double precision,
    max_price double precision,
    sku character varying(191),
    bar_code character varying(250),
    quantity integer NOT NULL,
    in_stock boolean NOT NULL,
    is_taxable boolean NOT NULL,
    status public.productstatus NOT NULL,
    product_type public.producttype NOT NULL,
    height double precision,
    width double precision,
    length double precision,
    dimension_unit character varying(30),
    image json,
    video json,
    deleted_at timestamp without time zone,
    is_digital boolean NOT NULL,
    is_external boolean NOT NULL,
    external_product_url character varying(191),
    external_product_button_text character varying(191),
    category_id integer NOT NULL,
    shop_id integer,
    unit character varying(191),
    gallery json,
    is_feature boolean,
    manufacturer_id integer,
    meta_title character varying,
    meta_description character varying,
    warranty character varying,
    return_policy character varying,
    shipping_info character varying,
    tags json,
    weight double precision,
    attributes json,
    total_purchased_quantity integer NOT NULL,
    total_sold_quantity integer NOT NULL
);


ALTER TABLE public.products OWNER TO neondb_owner;

--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.products_id_seq OWNER TO neondb_owner;

--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.products_id_seq OWNED BY public.products.id;


--
-- Name: return_items; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.return_items (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    return_request_id integer NOT NULL,
    order_item_id integer NOT NULL,
    product_id integer NOT NULL,
    variation_option_id integer,
    quantity integer NOT NULL,
    unit_price double precision NOT NULL,
    refund_amount double precision NOT NULL
);


ALTER TABLE public.return_items OWNER TO neondb_owner;

--
-- Name: return_items_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.return_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.return_items_id_seq OWNER TO neondb_owner;

--
-- Name: return_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.return_items_id_seq OWNED BY public.return_items.id;


--
-- Name: return_requests; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.return_requests (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    order_id integer NOT NULL,
    user_id integer NOT NULL,
    return_type public.returntype NOT NULL,
    reason character varying(1000) NOT NULL,
    status public.returnstatus NOT NULL,
    refund_amount double precision NOT NULL,
    refund_status public.refundstatus NOT NULL,
    wallet_credit_id integer,
    transfer_eligible_at timestamp without time zone,
    transferred_at timestamp without time zone,
    admin_notes character varying,
    rejected_reason character varying
);


ALTER TABLE public.return_requests OWNER TO neondb_owner;

--
-- Name: return_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.return_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.return_requests_id_seq OWNER TO neondb_owner;

--
-- Name: return_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.return_requests_id_seq OWNED BY public.return_requests.id;


--
-- Name: reviews; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.reviews (
    id integer NOT NULL,
    order_id integer NOT NULL,
    user_id integer NOT NULL,
    shop_id integer NOT NULL,
    product_id integer NOT NULL,
    variation_option_id integer,
    comment character varying,
    rating integer NOT NULL,
    photos json,
    deleted_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone
);


ALTER TABLE public.reviews OWNER TO neondb_owner;

--
-- Name: reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reviews_id_seq OWNER TO neondb_owner;

--
-- Name: reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.reviews_id_seq OWNED BY public.reviews.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.roles (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    description character varying,
    permissions json NOT NULL,
    is_active boolean NOT NULL,
    user_id integer NOT NULL,
    slug character varying(60) NOT NULL
);


ALTER TABLE public.roles OWNER TO neondb_owner;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.roles_id_seq OWNER TO neondb_owner;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: settings; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.settings (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    options json NOT NULL,
    language character varying NOT NULL
);


ALTER TABLE public.settings OWNER TO neondb_owner;

--
-- Name: settings_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.settings_id_seq OWNER TO neondb_owner;

--
-- Name: settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.settings_id_seq OWNED BY public.settings.id;


--
-- Name: shipping_classes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.shipping_classes (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    name character varying(191) NOT NULL,
    slug character varying(191) NOT NULL,
    amount double precision NOT NULL,
    is_global boolean NOT NULL,
    is_active boolean NOT NULL,
    language character varying(191) NOT NULL,
    type public.shippingtype
);


ALTER TABLE public.shipping_classes OWNER TO neondb_owner;

--
-- Name: shipping_classes_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.shipping_classes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.shipping_classes_id_seq OWNER TO neondb_owner;

--
-- Name: shipping_classes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.shipping_classes_id_seq OWNED BY public.shipping_classes.id;


--
-- Name: shop_earnings; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.shop_earnings (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    shop_id integer NOT NULL,
    order_id integer NOT NULL,
    order_amount numeric(12,2) NOT NULL,
    admin_commission numeric(12,2) NOT NULL,
    shop_earning numeric(12,2) NOT NULL,
    is_settled boolean NOT NULL,
    settled_at timestamp without time zone,
    order_product_id integer NOT NULL
);


ALTER TABLE public.shop_earnings OWNER TO neondb_owner;

--
-- Name: shop_earnings_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.shop_earnings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.shop_earnings_id_seq OWNER TO neondb_owner;

--
-- Name: shop_earnings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.shop_earnings_id_seq OWNED BY public.shop_earnings.id;


--
-- Name: shop_withdraw_requests; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.shop_withdraw_requests (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    shop_id integer NOT NULL,
    amount numeric(12,2) NOT NULL,
    admin_commission numeric(12,2) NOT NULL,
    net_amount numeric(12,2) NOT NULL,
    status public.withdrawstatus NOT NULL,
    payment_method public.paymentmethod NOT NULL,
    bank_name character varying(255),
    account_number character varying(50),
    account_holder_name character varying(255),
    ifsc_code character varying(20),
    cash_handled_by integer,
    cash_payment_date timestamp without time zone,
    processed_by integer,
    processed_at timestamp without time zone,
    rejection_reason character varying
);


ALTER TABLE public.shop_withdraw_requests OWNER TO neondb_owner;

--
-- Name: shop_withdraw_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.shop_withdraw_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.shop_withdraw_requests_id_seq OWNER TO neondb_owner;

--
-- Name: shop_withdraw_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.shop_withdraw_requests_id_seq OWNED BY public.shop_withdraw_requests.id;


--
-- Name: shops; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.shops (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    owner_id integer NOT NULL,
    name character varying(191),
    slug character varying(191),
    description character varying,
    cover_image jsonb,
    logo jsonb,
    is_active boolean NOT NULL,
    address jsonb,
    settings jsonb,
    notifications jsonb
);


ALTER TABLE public.shops OWNER TO neondb_owner;

--
-- Name: shops_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.shops_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.shops_id_seq OWNER TO neondb_owner;

--
-- Name: shops_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.shops_id_seq OWNED BY public.shops.id;


--
-- Name: tax_classes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.tax_classes (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    name character varying(191) NOT NULL,
    country character varying(191),
    state character varying(191),
    zip character varying(191),
    city character varying(191),
    rate double precision NOT NULL,
    is_global boolean NOT NULL,
    priority integer NOT NULL,
    on_shipping boolean NOT NULL
);


ALTER TABLE public.tax_classes OWNER TO neondb_owner;

--
-- Name: tax_classes_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.tax_classes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tax_classes_id_seq OWNER TO neondb_owner;

--
-- Name: tax_classes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.tax_classes_id_seq OWNED BY public.tax_classes.id;


--
-- Name: user_roles; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_roles (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    user_id integer NOT NULL,
    role_id integer NOT NULL
);


ALTER TABLE public.user_roles OWNER TO neondb_owner;

--
-- Name: user_roles_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.user_roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_roles_id_seq OWNER TO neondb_owner;

--
-- Name: user_roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.user_roles_id_seq OWNED BY public.user_roles.id;


--
-- Name: user_shop; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_shop (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    user_id integer NOT NULL,
    shop_id integer NOT NULL
);


ALTER TABLE public.user_shop OWNER TO neondb_owner;

--
-- Name: user_shop_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.user_shop_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_shop_id_seq OWNER TO neondb_owner;

--
-- Name: user_shop_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.user_shop_id_seq OWNED BY public.user_shop.id;


--
-- Name: user_wallets; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_wallets (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    user_id integer NOT NULL,
    balance double precision NOT NULL,
    total_credited double precision NOT NULL,
    total_debited double precision NOT NULL
);


ALTER TABLE public.user_wallets OWNER TO neondb_owner;

--
-- Name: user_wallets_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.user_wallets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_wallets_id_seq OWNER TO neondb_owner;

--
-- Name: user_wallets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.user_wallets_id_seq OWNED BY public.user_wallets.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.users (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    name character varying(191) NOT NULL,
    email character varying(191) NOT NULL,
    phone_no character varying(30) NOT NULL,
    email_verified_at timestamp without time zone,
    password character varying,
    remember_token character varying(100),
    is_active boolean NOT NULL,
    is_root boolean DEFAULT false NOT NULL
);


ALTER TABLE public.users OWNER TO neondb_owner;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO neondb_owner;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: variation_options; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.variation_options (
    id integer NOT NULL,
    title character varying(191) NOT NULL,
    image json,
    price character varying(191) NOT NULL,
    sale_price character varying(191),
    purchase_price double precision,
    language character varying(191) DEFAULT 'en'::character varying NOT NULL,
    quantity integer NOT NULL,
    is_disable boolean DEFAULT false NOT NULL,
    sku character varying(191),
    options json,
    product_id integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    is_digital boolean DEFAULT false NOT NULL,
    bar_code character varying(250),
    is_active boolean NOT NULL
);


ALTER TABLE public.variation_options OWNER TO neondb_owner;

--
-- Name: variation_options_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.variation_options_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.variation_options_id_seq OWNER TO neondb_owner;

--
-- Name: variation_options_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.variation_options_id_seq OWNED BY public.variation_options.id;


--
-- Name: wallet_transactions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.wallet_transactions (
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    id integer NOT NULL,
    user_id integer NOT NULL,
    amount double precision NOT NULL,
    transaction_type character varying NOT NULL,
    balance_after double precision NOT NULL,
    description character varying,
    is_refund boolean NOT NULL,
    transfer_eligible_at timestamp without time zone,
    transferred_to_bank boolean NOT NULL,
    transferred_at timestamp without time zone,
    return_request_id integer
);


ALTER TABLE public.wallet_transactions OWNER TO neondb_owner;

--
-- Name: wallet_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.wallet_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.wallet_transactions_id_seq OWNER TO neondb_owner;

--
-- Name: wallet_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.wallet_transactions_id_seq OWNED BY public.wallet_transactions.id;


--
-- Name: wishlists; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.wishlists (
    id integer NOT NULL,
    user_id integer NOT NULL,
    product_id integer NOT NULL,
    variation_option_id integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone
);


ALTER TABLE public.wishlists OWNER TO neondb_owner;

--
-- Name: wishlists_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.wishlists_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.wishlists_id_seq OWNER TO neondb_owner;

--
-- Name: wishlists_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.wishlists_id_seq OWNED BY public.wishlists.id;


--
-- Name: address id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.address ALTER COLUMN id SET DEFAULT nextval('public.address_id_seq'::regclass);


--
-- Name: attribute_product id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.attribute_product ALTER COLUMN id SET DEFAULT nextval('public.attribute_product_id_seq'::regclass);


--
-- Name: attribute_values id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.attribute_values ALTER COLUMN id SET DEFAULT nextval('public.attribute_values_id_seq'::regclass);


--
-- Name: attributes id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.attributes ALTER COLUMN id SET DEFAULT nextval('public.attributes_id_seq'::regclass);


--
-- Name: banners id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.banners ALTER COLUMN id SET DEFAULT nextval('public.banners_id_seq'::regclass);


--
-- Name: carts id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.carts ALTER COLUMN id SET DEFAULT nextval('public.carts_id_seq'::regclass);


--
-- Name: categories id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.categories ALTER COLUMN id SET DEFAULT nextval('public.categories_id_seq'::regclass);


--
-- Name: coupons id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.coupons ALTER COLUMN id SET DEFAULT nextval('public.coupons_id_seq'::regclass);


--
-- Name: email_template id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.email_template ALTER COLUMN id SET DEFAULT nextval('public.email_template_id_seq'::regclass);


--
-- Name: faqs id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.faqs ALTER COLUMN id SET DEFAULT nextval('public.faqs_id_seq'::regclass);


--
-- Name: manufacturers id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.manufacturers ALTER COLUMN id SET DEFAULT nextval('public.manufacturers_id_seq'::regclass);


--
-- Name: media id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.media ALTER COLUMN id SET DEFAULT nextval('public.media_id_seq'::regclass);


--
-- Name: order_product id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.order_product ALTER COLUMN id SET DEFAULT nextval('public.order_product_id_seq'::regclass);


--
-- Name: orders id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);


--
-- Name: orders_status id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders_status ALTER COLUMN id SET DEFAULT nextval('public.orders_status_id_seq'::regclass);


--
-- Name: product_import_history id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_import_history ALTER COLUMN id SET DEFAULT nextval('public.product_import_history_id_seq'::regclass);


--
-- Name: product_purchase id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_purchase ALTER COLUMN id SET DEFAULT nextval('public.product_purchase_id_seq'::regclass);


--
-- Name: product_purchase_variation_options id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_purchase_variation_options ALTER COLUMN id SET DEFAULT nextval('public.product_purchase_variation_options_id_seq'::regclass);


--
-- Name: products id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.products ALTER COLUMN id SET DEFAULT nextval('public.products_id_seq'::regclass);


--
-- Name: return_items id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.return_items ALTER COLUMN id SET DEFAULT nextval('public.return_items_id_seq'::regclass);


--
-- Name: return_requests id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.return_requests ALTER COLUMN id SET DEFAULT nextval('public.return_requests_id_seq'::regclass);


--
-- Name: reviews id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reviews ALTER COLUMN id SET DEFAULT nextval('public.reviews_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: settings id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.settings ALTER COLUMN id SET DEFAULT nextval('public.settings_id_seq'::regclass);


--
-- Name: shipping_classes id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipping_classes ALTER COLUMN id SET DEFAULT nextval('public.shipping_classes_id_seq'::regclass);


--
-- Name: shop_earnings id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shop_earnings ALTER COLUMN id SET DEFAULT nextval('public.shop_earnings_id_seq'::regclass);


--
-- Name: shop_withdraw_requests id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shop_withdraw_requests ALTER COLUMN id SET DEFAULT nextval('public.shop_withdraw_requests_id_seq'::regclass);


--
-- Name: shops id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shops ALTER COLUMN id SET DEFAULT nextval('public.shops_id_seq'::regclass);


--
-- Name: tax_classes id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.tax_classes ALTER COLUMN id SET DEFAULT nextval('public.tax_classes_id_seq'::regclass);


--
-- Name: user_roles id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_roles ALTER COLUMN id SET DEFAULT nextval('public.user_roles_id_seq'::regclass);


--
-- Name: user_shop id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_shop ALTER COLUMN id SET DEFAULT nextval('public.user_shop_id_seq'::regclass);


--
-- Name: user_wallets id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_wallets ALTER COLUMN id SET DEFAULT nextval('public.user_wallets_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: variation_options id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.variation_options ALTER COLUMN id SET DEFAULT nextval('public.variation_options_id_seq'::regclass);


--
-- Name: wallet_transactions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallet_transactions ALTER COLUMN id SET DEFAULT nextval('public.wallet_transactions_id_seq'::regclass);


--
-- Name: wishlists id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wishlists ALTER COLUMN id SET DEFAULT nextval('public.wishlists_id_seq'::regclass);


--
-- Data for Name: address; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.address (created_at, updated_at, id, title, type, is_default, address, location, customer_id) FROM stdin;
2025-10-08 07:21:41.491485	\N	1	Billing Addres	billing	t	{"street": "Rawalpindi", "city": "Islamabad", "state": "Federal", "postal_code": null, "country": "Pakistan"}	null	11
2025-10-08 07:22:33.957249	\N	2	Shipping Addres	shipping	t	{"street": "Rawalpindi", "city": "Islamabad", "state": "Federal", "postal_code": null, "country": "Pakistan"}	{"lat": 1.0, "lng": 2.0}	11
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.alembic_version (version_num) FROM stdin;
dbc11bf15b15
\.


--
-- Data for Name: attribute_product; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.attribute_product (created_at, updated_at, id, attribute_value_id, product_id) FROM stdin;
\.


--
-- Data for Name: attribute_values; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.attribute_values (created_at, updated_at, id, slug, attribute_id, value, language, meta) FROM stdin;
2025-10-11 04:37:14.221517	\N	7	small	6	Small	en	S
2025-10-11 04:37:14.648356	\N	8	medium	6	Medium	en	M
2025-10-11 04:37:15.895198	\N	9	large	6	Large	en	L
2025-10-11 04:37:16.313994	\N	10	extra-large	6	Extra Large	en	XL
2025-10-11 04:37:16.732333	\N	11	double-extra-large	6	Double Extra Large	en	XXL
2025-10-01 06:01:12.119185	\N	5	red-1	5	Red	en	#FF0000
2025-10-01 06:01:12.549948	\N	6	green-1	5	Green	en	#008000
2025-10-18 15:51:43.561458	\N	12	blue	5	Blue	en	#0000FF
\.


--
-- Data for Name: attributes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.attributes (created_at, updated_at, id, slug, language, name) FROM stdin;
2025-10-11 04:37:13.156512	\N	6	size	en	Size
2025-10-01 06:01:10.951519	2025-10-18 15:44:55.895908	5	color	en	color
\.


--
-- Data for Name: banners; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.banners (created_at, updated_at, id, category_id, name, slug, language, description, is_active, image) FROM stdin;
2025-10-01 09:32:32.84414	\N	3	\N	Super Sauda	super-sauda	en	Super Sauda	t	{"id": 106, "filename": "banner3.avif", "extension": ".avif", "original": "https://api.ctspk.com/media/admin@example.com/banner3.avif", "size_mb": 0.06, "thumbnail": null, "media_type": "image"}
2025-10-01 09:33:35.064016	\N	4	\N	Premium Home Appliance	premium-home-appliance	en	Premium Home Appliance	t	{"id": 107, "filename": "banner4.avif", "extension": ".avif", "original": "https://api.ctspk.com/media/admin@example.com/banner4.avif", "size_mb": 0.02, "thumbnail": null, "media_type": "image"}
2025-10-01 08:49:02.611796	2025-10-01 14:32:12.915931	2	\N	Clearence Sale	clearence-sale	en	Clearence Sale	t	{"id": 105, "filename": "banner2.avif", "extension": ".avif", "original": "https://api.ctspk.com/media/admin@example.com/banner2.avif", "size_mb": 0.05, "thumbnail": null, "media_type": "image"}
2024-01-12 18:17:50	2025-10-05 15:15:31.187901	48	\N	Join Our Community	join-our-community	en	Join Our Community for best deals	t	{"id": 104, "filename": "banner-01.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/banner-01.webp", "size_mb": 0.05, "thumbnail": null, "media_type": "image"}
2025-10-05 15:16:21.21073	\N	5	\N	wardrobe weeken	wardrobe-weeken	en	brand	t	{"id": 132, "filename": "banner5.avif", "extension": ".avif", "original": "https://api.ctspk.com/media/admin@example.com/banner5.avif", "size_mb": 0.05, "thumbnail": null, "media_type": "image"}
2025-10-05 16:47:54.383637	\N	6	5	Banner Old	banner-old	en	Test Banner	t	{"id": 131, "filename": "home-banner1.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/home-banner1.webp", "size_mb": 0.05, "thumbnail": null, "media_type": "image"}
\.


--
-- Data for Name: carts; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.carts (created_at, updated_at, id, product_id, user_id, shop_id, quantity) FROM stdin;
2025-10-19 04:38:33.753762	\N	32	259	9	3	1
\.


--
-- Data for Name: categories; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.categories (created_at, updated_at, id, parent_id, name, slug, level, language, icon, image, details, admin_commission_rate, is_active, deleted_at, root_id, seo_description, seo_keywords, seo_title) FROM stdin;
2025-10-12 17:40:24.377548	2025-10-18 13:39:38.674429	39	\N	Electronics	electronics	1	en	\N	\N	\N	\N	t	\N	39	\N	\N	\N
2025-10-12 17:40:27.379423	2025-10-18 13:39:59.615943	40	\N	Home & Kitchen	home-kitchen	1	en	\N	\N	\N	\N	t	\N	40	\N	\N	\N
2024-01-12 19:11:48	2025-10-01 14:24:48.996271	6	\N	Shoes	shoes-1	1	en	fa fa-cloths	null	Shoes Main Category	\N	t	\N	6	\N	\N	\N
2024-01-13 10:08:06	2025-09-26 01:25:44.354041	15	14	Cat Food	cat-food	3	en	\N	{"original": "https://api.ctspk.com/media/admin@example.com/cat-food.svg"}	Food for Cats	12	t	\N	5	\N	\N	\N
2024-01-12 18:17:50	2025-10-01 06:02:53.856733	5	\N	Grocery	grocery-1	1	en	fa fa-grocery	{"id": 93, "filename": "download.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/download.webp", "thumbnail": null, "media_type": "image"}	Grocery Main Category	\N	t	\N	5	\N	\N	\N
2024-01-13 10:06:55	2025-09-26 01:59:55.058089	14	5	Pet Food	pet-food	2	en	string	{"id":154,"filename":"pet-food_16779323.webp","extension":".webp","original":"https://api.ctspk.com/media/admin@example.com/pet-food_16779323.webp","size_mb":0.01,"thumbnail":null,"media_type":"image"}	Pet Food	0	t	\N	5	\N	\N	\N
2024-01-12 18:21:37	2024-01-12 18:21:37	7	5	Cooking Essentials	cooking-essentials	2	en	\N	{"id":155,"filename":"Kitchen-Utensils.svg","extension":".svg","original":"https://api.ctspk.com/media/admin@example.com/Kitchen-Utensils.svg","size_mb":0.05,"thumbnail":null,"media_type":"image"}	Cooking Essentials	5	t	\N	5	\N	\N	\N
2024-01-12 18:22:31	2024-01-12 23:26:18	8	7	Oil & Ghee	oil-ghee	3	en	\N	null	Oil & Ghee	10	t	\N	5	\N	\N	\N
2024-01-12 19:44:44	2024-01-12 19:44:44	9	5	Beverages	beverages	2	en	\N	null	Beverages	\N	t	\N	5	\N	\N	\N
2024-01-12 19:47:10	2024-01-12 22:11:26	10	9	Iced Tea and Coffee	iced-tea-and-coffee	3	en	\N	null	Iced Tea and Coffee	5	t	\N	5	\N	\N	\N
2024-01-12 23:19:27	2024-01-12 23:19:27	11	9	Water	water	3	en	\N	null	Water	10	t	\N	5	\N	\N	\N
2024-01-12 23:20:05	2024-01-12 23:20:05	12	9	Soft Drinks	soft-drinks	3	en	\N	null	Soft Drinks	10	t	\N	5	\N	\N	\N
2024-01-12 23:21:33	2024-01-12 23:21:33	13	9	Powder Drinks	powder-drinks	3	en	\N	null	Powder Drinks	10	t	\N	5	\N	\N	\N
2024-01-13 10:11:49	2024-01-13 10:11:49	16	14	Fish Food	fish-food	3	en	\N	null	Fish Food	5	t	\N	5	\N	\N	\N
2024-03-10 10:29:46	2024-03-10 10:29:46	21	5	Aerosols	aerosols	2	en	\N	null	Aerosols Insecticides	\N	t	\N	5	\N	\N	\N
2025-07-18 18:12:50	2025-07-18 18:12:50	23	5	Accessories	accessories-2	2	en	\N	null	\N	\N	t	\N	5	\N	\N	\N
2024-03-02 19:42:59	2024-03-02 19:42:59	25	6	Gents	gents	2	en	\N	null	For Gents	\N	t	\N	6	\N	\N	\N
2024-03-02 20:06:06	2024-03-02 20:06:06	27	25	Slippers	slippers-2	3	en	\N	null	Slippers for Men	10	t	\N	6	\N	\N	\N
2024-03-02 19:43:36	2024-03-02 19:43:36	28	6	Ladies	ladies	2	en	\N	null	For Females	\N	t	\N	6	\N	\N	\N
2024-03-02 20:02:29	2024-03-02 20:02:29	29	28	Flip-Flops	flip-flops-2	3	en	\N	null	Flip-Flops for Ladies	10	t	\N	6	\N	\N	\N
2024-03-02 20:05:31	2024-03-02 20:05:31	30	28	Slippers	slippers	3	en	\N	null	Slippers for Ladies	10	t	\N	6	\N	\N	\N
2024-01-13 10:13:03	2024-01-13 10:13:03	17	14	Dog Food	dog-food	3	en	\N	null	Dog Food	17	t	\N	5	\N	\N	\N
2024-01-13 13:53:04	2024-01-13 13:53:04	18	14	Bird Food	bird-food	3	en	\N	null	Birds Food	10	t	\N	5	\N	\N	\N
2024-03-08 21:00:59	2024-03-08 21:00:59	19	7	Grains & Seeds	grains-seeds	3	en	\N	null	\N	10	t	\N	5	\N	\N	\N
2024-03-08 21:08:29	2024-03-08 21:08:29	20	7	Sugar	sugar	3	en	\N	null	\N	10	t	\N	5	\N	\N	\N
2024-03-10 10:30:18	2024-03-10 10:30:18	22	21	Insecticides	insecticides	3	en	\N	null	Insecticides Products	10	t	\N	5	\N	\N	\N
2025-07-18 18:13:42	2025-07-18 18:13:42	24	23	Sun Glasses	sun-glasses	3	en	\N	null	\N	20	t	\N	5	\N	\N	\N
2024-03-02 19:51:29	2024-03-02 19:51:29	26	25	Flip-Flops	flip-flops	3	en	\N	null	Flip-Flops	10	t	\N	6	\N	\N	\N
2024-03-02 19:44:21	2024-03-02 19:44:21	31	6	Kids	kids	2	en	\N	null	For Kids	\N	t	\N	6	\N	\N	\N
2024-03-02 20:14:30	2024-03-02 20:14:30	32	31	School Shoes	school-shoes	3	en	\N	null	School Shoes for Kids	10	t	\N	6	\N	\N	\N
2024-03-02 19:45:16	2024-03-02 19:45:16	33	6	Accessories	accessories	2	en	\N	null	Shoe Accessories	\N	t	\N	6	\N	\N	\N
\.


--
-- Data for Name: coupons; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.coupons (created_at, updated_at, id, code, language, description, image, type, amount, minimum_cart_amount, active_from, expire_at, deleted_at) FROM stdin;
2025-10-08 07:29:05.8537	\N	1	Flat50	en	Flat Description	{"id": 93, "filename": "download.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/download.webp", "thumbnail": null, "media_type": "image"}	FIXED	50	3000	2025-10-08 07:26:02.365	2025-10-31 07:26:02.365	\N
2025-10-09 03:27:38.940587	\N	2	flat 20	en	flat 20 percentage discont on all product 	{"id": 108, "filename": "9899431.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/9899431.webp", "size_mb": 0.14, "thumbnail": null, "media_type": "image"}	PERCENTAGE	20	3000	2025-10-08 20:01:00	2025-10-31 18:59:00	\N
2025-10-18 13:50:37.620168	\N	3	Eidi 	en		null	FIXED	500	5000	2025-10-18 13:50:00	2025-10-30 13:50:00	\N
\.


--
-- Data for Name: email_template; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.email_template (created_at, updated_at, id, name, slug, subject, content, is_active, language, html_content) FROM stdin;
2025-10-03 02:14:47.255907	2025-10-19 02:41:37.623612	3	Reset Password Link	reset-password-link-1	Reset Password Link send to customer	{"body": {"id": "6TqAk2_ZpJ", "rows": [{"id": "nnH6z7hX8W", "cells": [1], "values": {"_meta": {"htmlID": "u_row_2", "htmlClassNames": "u_row"}, "anchor": "", "border": {}, "locked": false, "columns": false, "padding": "0px", "hideable": true, "deletable": true, "draggable": true, "selectable": true, "_styleGuide": null, "hideDesktop": false, "duplicatable": true, "backgroundColor": "#FFFFFF", "backgroundImage": {"url": "", "size": "custom", "repeat": "no-repeat", "position": "center", "fullWidth": true}, "displayCondition": null, "backgroundColorImage": {}, "columnsBackgroundColor": ""}, "columns": [{"id": "Vxhg3z3k6s", "values": {"_meta": {"htmlID": "u_column_2", "htmlClassNames": "u_column"}, "width": "100%", "border": {}, "padding": "0px", "deletable": true, "backgroundColor": ""}, "contents": [{"id": "V8sS3s3k6s", "type": "text", "values": {"text": "<h1>Welcome!</h1><p>Start designing your email template here.</p><p>Use the <strong>Insert Tag</strong> button to add dynamic content.</p> {{subject}} {{addcc}}", "_meta": {"htmlID": "u_content_text_1", "htmlClassNames": "u_content_text"}, "anchor": "", "locked": false, "fontSize": "14px", "hideable": true, "deletable": true, "draggable": true, "linkStyle": {"inherit": true, "linkColor": "#0000ee", "linkUnderline": true, "linkHoverColor": "#0000ee", "linkHoverUnderline": true}, "textAlign": "left", "lineHeight": "140%", "selectable": true, "_styleGuide": null, "hideDesktop": false, "duplicatable": true, "containerPadding": "10px", "displayCondition": null}, "hasDeprecatedFontControls": true}, {"id": "Iwpcoc3bBH", "type": "text", "values": {"text": "<p style=\\"line-height: 140%;\\">My Text Block goes here</p>", "_meta": {"htmlID": "u_content_text_2", "htmlClassNames": "u_content_text"}, "anchor": "", "locked": false, "fontSize": "14px", "hideable": true, "deletable": true, "draggable": true, "linkStyle": {"inherit": true, "linkColor": "#0000ee", "linkUnderline": true, "linkHoverColor": "#0000ee", "linkHoverUnderline": true}, "textAlign": "left", "_languages": {}, "lineHeight": "140%", "selectable": true, "_styleGuide": null, "duplicatable": true, "containerPadding": "10px", "displayCondition": null}}]}]}], "values": {"_meta": {"htmlID": "u_body", "htmlClassNames": "u_body"}, "language": {}, "linkStyle": {"body": true, "linkColor": "#0000EE", "linkUnderline": true, "linkHoverColor": "#0000EE", "linkHoverUnderline": true}, "textColor": "#000000", "fontFamily": {"label": "Arial", "value": "arial,helvetica,sans-serif"}, "popupWidth": "600px", "_styleGuide": null, "popupHeight": "auto", "borderRadius": "10px", "contentAlign": "center", "contentWidth": "600px", "popupPosition": "center", "preheaderText": "", "backgroundColor": "#FFFFFF", "backgroundImage": {"url": "", "size": "custom", "repeat": "no-repeat", "position": "top-left", "fullWidth": true, "customPosition": ["0%", "0%"]}, "popupDisplayDelay": 0, "contentVerticalAlign": "center", "popupBackgroundColor": "#FFFFFF", "popupBackgroundImage": {"url": "", "size": "cover", "repeat": "no-repeat", "position": "center", "fullWidth": true}, "popupCloseButton_action": {"name": "close_popup", "attrs": {"onClick": "document.querySelector('.u-popup-container').style.display = 'none';"}}, "popupCloseButton_margin": "0px", "popupCloseButton_position": "top-right", "popupCloseButton_iconColor": "#000000", "popupOverlay_backgroundColor": "rgba(0, 0, 0, 0.1)", "popupCloseButton_borderRadius": "0px", "popupCloseButton_backgroundColor": "#DDDDDD"}, "footers": [], "headers": []}, "counters": {"u_row": 2, "u_column": 2, "u_content_text": 2}, "schemaVersion": 21}	t	en	<!DOCTYPE HTML PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">\n<head>\n<!--[if gte mso 9]>\n<xml>\n  <o:OfficeDocumentSettings>\n    <o:AllowPNG/>\n    <o:PixelsPerInch>96</o:PixelsPerInch>\n  </o:OfficeDocumentSettings>\n</xml>\n<![endif]-->\n  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <meta name="x-apple-disable-message-reformatting">\n  <!--[if !mso]><!--><meta http-equiv="X-UA-Compatible" content="IE=edge"><!--<![endif]-->\n  <title></title>\n  \n    <style type="text/css">\n      \n      @media only screen and (min-width: 620px) {\n        .u-row {\n          width: 600px !important;\n        }\n\n        .u-row .u-col {\n          vertical-align: top;\n        }\n\n        \n            .u-row .u-col-100 {\n              width: 600px !important;\n            }\n          \n      }\n\n      @media only screen and (max-width: 620px) {\n        .u-row-container {\n          max-width: 100% !important;\n          padding-left: 0px !important;\n          padding-right: 0px !important;\n        }\n\n        .u-row {\n          width: 100% !important;\n        }\n\n        .u-row .u-col {\n          display: block !important;\n          width: 100% !important;\n          min-width: 320px !important;\n          max-width: 100% !important;\n        }\n\n        .u-row .u-col > div {\n          margin: 0 auto;\n        }\n\n\n}\n    \nbody{margin:0;padding:0}table,td,tr{border-collapse:collapse;vertical-align:top}p{margin:0}.ie-container table,.mso-container table{table-layout:fixed}*{line-height:inherit}a[x-apple-data-detectors=true]{color:inherit!important;text-decoration:none!important}\n\n\ntable, td { color: #000000; } </style>\n  \n  \n\n</head>\n\n<body class="clean-body u_body" style="margin: 0;padding: 0;-webkit-text-size-adjust: 100%;background-color: #FFFFFF;color: #000000">\n  <!--[if IE]><div class="ie-container"><![endif]-->\n  <!--[if mso]><div class="mso-container"><![endif]-->\n  <table role="presentation" style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;min-width: 320px;Margin: 0 auto;background-color: #FFFFFF;width:100%" cellpadding="0" cellspacing="0">\n  <tbody>\n  <tr style="vertical-align: top">\n    <td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top">\n    <!--[if (mso)|(IE)]><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="background-color: #FFFFFF;"><![endif]-->\n    \n  \n  \n<div class="u-row-container" style="padding: 0px;background-color: #FFFFFF">\n  <div class="u-row" style="margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: transparent;">\n    <div style="border-collapse: collapse;display: table;width: 100%;height: 100%;background-color: transparent;">\n      <!--[if (mso)|(IE)]><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: #FFFFFF;" align="center"><table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: transparent;"><![endif]-->\n      \n<!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]-->\n<div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;">\n  <div style="height: 100%;width: 100% !important;">\n  <!--[if (!mso)&(!IE)]><!--><div style="box-sizing: border-box; height: 100%; padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]-->\n  \n<table style="font-family:arial,helvetica,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">\n  <tbody>\n    <tr>\n      <td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:arial,helvetica,sans-serif;" align="left">\n        \n  <div style="font-size: 14px; line-height: 140%; text-align: left; word-wrap: break-word;">\n    <h1>Welcome!</h1><p>Start designing your email template here.</p><p>Use the <strong>Insert Tag</strong> button to add dynamic content.</p> {{subject}} {{addcc}}\n  </div>\n\n      </td>\n    </tr>\n  </tbody>\n</table>\n\n<table style="font-family:arial,helvetica,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">\n  <tbody>\n    <tr>\n      <td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:arial,helvetica,sans-serif;" align="left">\n        \n  <div style="font-size: 14px; line-height: 140%; text-align: left; word-wrap: break-word;">\n    <p style="line-height: 140%;">My Text Block goes here</p>\n  </div>\n\n      </td>\n    </tr>\n  </tbody>\n</table>\n\n  <!--[if (!mso)&(!IE)]><!--></div><!--<![endif]-->\n  </div>\n</div>\n<!--[if (mso)|(IE)]></td><![endif]-->\n      <!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]-->\n    </div>\n  </div>\n  </div>\n  \n\n\n    <!--[if (mso)|(IE)]></td></tr></table><![endif]-->\n    </td>\n  </tr>\n  </tbody>\n  </table>\n  <!--[if mso]></div><![endif]-->\n  <!--[if IE]></div><![endif]-->\n</body>\n\n</html>\n
2025-10-19 05:24:25.092916	\N	6	Reset Password Link (Copy)	reset-password-link-copy	Reset Password Link send to customer	{"body": {"id": "6TqAk2_ZpJ", "rows": [{"id": "nnH6z7hX8W", "cells": [1], "values": {"_meta": {"htmlID": "u_row_2", "htmlClassNames": "u_row"}, "anchor": "", "border": {}, "locked": false, "columns": false, "padding": "0px", "hideable": true, "deletable": true, "draggable": true, "selectable": true, "_styleGuide": null, "hideDesktop": false, "duplicatable": true, "backgroundColor": "#FFFFFF", "backgroundImage": {"url": "", "size": "custom", "repeat": "no-repeat", "position": "center", "fullWidth": true}, "displayCondition": null, "backgroundColorImage": {}, "columnsBackgroundColor": ""}, "columns": [{"id": "Vxhg3z3k6s", "values": {"_meta": {"htmlID": "u_column_2", "htmlClassNames": "u_column"}, "width": "100%", "border": {}, "padding": "0px", "deletable": true, "backgroundColor": ""}, "contents": [{"id": "V8sS3s3k6s", "type": "text", "values": {"text": "<h1>Welcome!</h1><p>Start designing your email template here.</p><p>Use the <strong>Insert Tag</strong> button to add dynamic content.</p> {{subject}} {{addcc}}", "_meta": {"htmlID": "u_content_text_1", "htmlClassNames": "u_content_text"}, "anchor": "", "locked": false, "fontSize": "14px", "hideable": true, "deletable": true, "draggable": true, "linkStyle": {"inherit": true, "linkColor": "#0000ee", "linkUnderline": true, "linkHoverColor": "#0000ee", "linkHoverUnderline": true}, "textAlign": "left", "lineHeight": "140%", "selectable": true, "_styleGuide": null, "hideDesktop": false, "duplicatable": true, "containerPadding": "10px", "displayCondition": null}, "hasDeprecatedFontControls": true}, {"id": "Iwpcoc3bBH", "type": "text", "values": {"text": "<p style=\\"line-height: 140%;\\">My Text Block goes here</p>", "_meta": {"htmlID": "u_content_text_2", "htmlClassNames": "u_content_text"}, "anchor": "", "locked": false, "fontSize": "14px", "hideable": true, "deletable": true, "draggable": true, "linkStyle": {"inherit": true, "linkColor": "#0000ee", "linkUnderline": true, "linkHoverColor": "#0000ee", "linkHoverUnderline": true}, "textAlign": "left", "_languages": {}, "lineHeight": "140%", "selectable": true, "_styleGuide": null, "duplicatable": true, "containerPadding": "10px", "displayCondition": null}}]}]}], "values": {"_meta": {"htmlID": "u_body", "htmlClassNames": "u_body"}, "language": {}, "linkStyle": {"body": true, "linkColor": "#0000EE", "linkUnderline": true, "linkHoverColor": "#0000EE", "linkHoverUnderline": true}, "textColor": "#000000", "fontFamily": {"label": "Arial", "value": "arial,helvetica,sans-serif"}, "popupWidth": "600px", "_styleGuide": null, "popupHeight": "auto", "borderRadius": "10px", "contentAlign": "center", "contentWidth": "600px", "popupPosition": "center", "preheaderText": "", "backgroundColor": "#FFFFFF", "backgroundImage": {"url": "", "size": "custom", "repeat": "no-repeat", "position": "top-left", "fullWidth": true, "customPosition": ["0%", "0%"]}, "popupDisplayDelay": 0, "contentVerticalAlign": "center", "popupBackgroundColor": "#FFFFFF", "popupBackgroundImage": {"url": "", "size": "cover", "repeat": "no-repeat", "position": "center", "fullWidth": true}, "popupCloseButton_action": {"name": "close_popup", "attrs": {"onClick": "document.querySelector('.u-popup-container').style.display = 'none';"}}, "popupCloseButton_margin": "0px", "popupCloseButton_position": "top-right", "popupCloseButton_iconColor": "#000000", "popupOverlay_backgroundColor": "rgba(0, 0, 0, 0.1)", "popupCloseButton_borderRadius": "0px", "popupCloseButton_backgroundColor": "#DDDDDD"}, "footers": [], "headers": []}, "counters": {"u_row": 2, "u_column": 2, "u_content_text": 2}, "schemaVersion": 21}	f	en	<!DOCTYPE HTML PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">\n<head>\n<!--[if gte mso 9]>\n<xml>\n  <o:OfficeDocumentSettings>\n    <o:AllowPNG/>\n    <o:PixelsPerInch>96</o:PixelsPerInch>\n  </o:OfficeDocumentSettings>\n</xml>\n<![endif]-->\n  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <meta name="x-apple-disable-message-reformatting">\n  <!--[if !mso]><!--><meta http-equiv="X-UA-Compatible" content="IE=edge"><!--<![endif]-->\n  <title></title>\n  \n    <style type="text/css">\n      \n      @media only screen and (min-width: 620px) {\n        .u-row {\n          width: 600px !important;\n        }\n\n        .u-row .u-col {\n          vertical-align: top;\n        }\n\n        \n            .u-row .u-col-100 {\n              width: 600px !important;\n            }\n          \n      }\n\n      @media only screen and (max-width: 620px) {\n        .u-row-container {\n          max-width: 100% !important;\n          padding-left: 0px !important;\n          padding-right: 0px !important;\n        }\n\n        .u-row {\n          width: 100% !important;\n        }\n\n        .u-row .u-col {\n          display: block !important;\n          width: 100% !important;\n          min-width: 320px !important;\n          max-width: 100% !important;\n        }\n\n        .u-row .u-col > div {\n          margin: 0 auto;\n        }\n\n\n}\n    \nbody{margin:0;padding:0}table,td,tr{border-collapse:collapse;vertical-align:top}p{margin:0}.ie-container table,.mso-container table{table-layout:fixed}*{line-height:inherit}a[x-apple-data-detectors=true]{color:inherit!important;text-decoration:none!important}\n\n\ntable, td { color: #000000; } </style>\n  \n  \n\n</head>\n\n<body class="clean-body u_body" style="margin: 0;padding: 0;-webkit-text-size-adjust: 100%;background-color: #FFFFFF;color: #000000">\n  <!--[if IE]><div class="ie-container"><![endif]-->\n  <!--[if mso]><div class="mso-container"><![endif]-->\n  <table role="presentation" style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;min-width: 320px;Margin: 0 auto;background-color: #FFFFFF;width:100%" cellpadding="0" cellspacing="0">\n  <tbody>\n  <tr style="vertical-align: top">\n    <td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top">\n    <!--[if (mso)|(IE)]><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="background-color: #FFFFFF;"><![endif]-->\n    \n  \n  \n<div class="u-row-container" style="padding: 0px;background-color: #FFFFFF">\n  <div class="u-row" style="margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: transparent;">\n    <div style="border-collapse: collapse;display: table;width: 100%;height: 100%;background-color: transparent;">\n      <!--[if (mso)|(IE)]><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: #FFFFFF;" align="center"><table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: transparent;"><![endif]-->\n      \n<!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]-->\n<div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;">\n  <div style="height: 100%;width: 100% !important;">\n  <!--[if (!mso)&(!IE)]><!--><div style="box-sizing: border-box; height: 100%; padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]-->\n  \n<table style="font-family:arial,helvetica,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">\n  <tbody>\n    <tr>\n      <td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:arial,helvetica,sans-serif;" align="left">\n        \n  <div style="font-size: 14px; line-height: 140%; text-align: left; word-wrap: break-word;">\n    <h1>Welcome!</h1><p>Start designing your email template here.</p><p>Use the <strong>Insert Tag</strong> button to add dynamic content.</p> {{subject}} {{addcc}}\n  </div>\n\n      </td>\n    </tr>\n  </tbody>\n</table>\n\n<table style="font-family:arial,helvetica,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">\n  <tbody>\n    <tr>\n      <td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:arial,helvetica,sans-serif;" align="left">\n        \n  <div style="font-size: 14px; line-height: 140%; text-align: left; word-wrap: break-word;">\n    <p style="line-height: 140%;">My Text Block goes here</p>\n  </div>\n\n      </td>\n    </tr>\n  </tbody>\n</table>\n\n  <!--[if (!mso)&(!IE)]><!--></div><!--<![endif]-->\n  </div>\n</div>\n<!--[if (mso)|(IE)]></td><![endif]-->\n      <!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]-->\n    </div>\n  </div>\n  </div>\n  \n\n\n    <!--[if (mso)|(IE)]></td></tr></table><![endif]-->\n    </td>\n  </tr>\n  </tbody>\n  </table>\n  <!--[if mso]></div><![endif]-->\n  <!--[if IE]></div><![endif]-->\n</body>\n\n</html>\n
2025-10-19 02:42:14.172614	2025-10-19 02:43:23.857558	5	Eid Promotions	eid-promotions	Reset Password Link send to customer	{"body": {"id": "6TqAk2_ZpJ", "rows": [{"id": "nnH6z7hX8W", "cells": [1], "values": {"_meta": {"htmlID": "u_row_2", "htmlClassNames": "u_row"}, "anchor": "", "border": {}, "locked": false, "columns": false, "padding": "0px", "hideable": true, "deletable": true, "draggable": true, "selectable": true, "_styleGuide": null, "hideDesktop": false, "duplicatable": true, "backgroundColor": "#FFFFFF", "backgroundImage": {"url": "", "size": "custom", "repeat": "no-repeat", "position": "center", "fullWidth": true}, "displayCondition": null, "backgroundColorImage": {}, "columnsBackgroundColor": ""}, "columns": [{"id": "Vxhg3z3k6s", "values": {"_meta": {"htmlID": "u_column_2", "htmlClassNames": "u_column"}, "width": "100%", "border": {}, "padding": "0px", "deletable": true, "backgroundColor": ""}, "contents": [{"id": "V8sS3s3k6s", "type": "text", "values": {"text": "<h1>Welcome!</h1><p>Start designing your email template here.</p><p>Use the <strong>Insert Tag</strong> button to add dynamic content.</p> {{subject}} {{addcc}}", "_meta": {"htmlID": "u_content_text_1", "htmlClassNames": "u_content_text"}, "anchor": "", "locked": false, "fontSize": "14px", "hideable": true, "deletable": true, "draggable": true, "linkStyle": {"inherit": true, "linkColor": "#0000ee", "linkUnderline": true, "linkHoverColor": "#0000ee", "linkHoverUnderline": true}, "textAlign": "left", "lineHeight": "140%", "selectable": true, "_styleGuide": null, "hideDesktop": false, "duplicatable": true, "containerPadding": "10px", "displayCondition": null}, "hasDeprecatedFontControls": true}, {"id": "Iwpcoc3bBH", "type": "text", "values": {"text": "<p style=\\"line-height: 140%;\\">Eid Mubarak!&nbsp;</p>", "_meta": {"htmlID": "u_content_text_2", "htmlClassNames": "u_content_text"}, "anchor": "", "locked": false, "fontSize": "14px", "hideable": true, "deletable": true, "draggable": true, "linkStyle": {"inherit": true, "linkColor": "#0000ee", "linkUnderline": true, "linkHoverColor": "#0000ee", "linkHoverUnderline": true}, "textAlign": "left", "_languages": {}, "lineHeight": "140%", "selectable": true, "_styleGuide": null, "hideDesktop": false, "duplicatable": true, "containerPadding": "10px", "displayCondition": null}}]}]}], "values": {"_meta": {"htmlID": "u_body", "htmlClassNames": "u_body"}, "language": {}, "linkStyle": {"body": true, "linkColor": "#0000EE", "linkUnderline": true, "linkHoverColor": "#0000EE", "linkHoverUnderline": true}, "textColor": "#000000", "fontFamily": {"label": "Arial", "value": "arial,helvetica,sans-serif"}, "popupWidth": "600px", "_styleGuide": null, "popupHeight": "auto", "borderRadius": "10px", "contentAlign": "center", "contentWidth": "600px", "popupPosition": "center", "preheaderText": "", "backgroundColor": "#FFFFFF", "backgroundImage": {"url": "", "size": "custom", "repeat": "no-repeat", "position": "top-left", "fullWidth": true, "customPosition": ["0%", "0%"]}, "popupDisplayDelay": 0, "contentVerticalAlign": "center", "popupBackgroundColor": "#FFFFFF", "popupBackgroundImage": {"url": "", "size": "cover", "repeat": "no-repeat", "position": "center", "fullWidth": true}, "popupCloseButton_action": {"name": "close_popup", "attrs": {"onClick": "document.querySelector('.u-popup-container').style.display = 'none';"}}, "popupCloseButton_margin": "0px", "popupCloseButton_position": "top-right", "popupCloseButton_iconColor": "#000000", "popupOverlay_backgroundColor": "rgba(0, 0, 0, 0.1)", "popupCloseButton_borderRadius": "0px", "popupCloseButton_backgroundColor": "#DDDDDD"}, "footers": [], "headers": []}, "counters": {"u_row": 2, "u_column": 2, "u_content_text": 2}, "schemaVersion": 21}	t	en	<!DOCTYPE HTML PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">\n<head>\n<!--[if gte mso 9]>\n<xml>\n  <o:OfficeDocumentSettings>\n    <o:AllowPNG/>\n    <o:PixelsPerInch>96</o:PixelsPerInch>\n  </o:OfficeDocumentSettings>\n</xml>\n<![endif]-->\n  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <meta name="x-apple-disable-message-reformatting">\n  <!--[if !mso]><!--><meta http-equiv="X-UA-Compatible" content="IE=edge"><!--<![endif]-->\n  <title></title>\n  \n    <style type="text/css">\n      \n      @media only screen and (min-width: 620px) {\n        .u-row {\n          width: 600px !important;\n        }\n\n        .u-row .u-col {\n          vertical-align: top;\n        }\n\n        \n            .u-row .u-col-100 {\n              width: 600px !important;\n            }\n          \n      }\n\n      @media only screen and (max-width: 620px) {\n        .u-row-container {\n          max-width: 100% !important;\n          padding-left: 0px !important;\n          padding-right: 0px !important;\n        }\n\n        .u-row {\n          width: 100% !important;\n        }\n\n        .u-row .u-col {\n          display: block !important;\n          width: 100% !important;\n          min-width: 320px !important;\n          max-width: 100% !important;\n        }\n\n        .u-row .u-col > div {\n          margin: 0 auto;\n        }\n\n\n}\n    \nbody{margin:0;padding:0}table,td,tr{border-collapse:collapse;vertical-align:top}p{margin:0}.ie-container table,.mso-container table{table-layout:fixed}*{line-height:inherit}a[x-apple-data-detectors=true]{color:inherit!important;text-decoration:none!important}\n\n\ntable, td { color: #000000; } </style>\n  \n  \n\n</head>\n\n<body class="clean-body u_body" style="margin: 0;padding: 0;-webkit-text-size-adjust: 100%;background-color: #FFFFFF;color: #000000">\n  <!--[if IE]><div class="ie-container"><![endif]-->\n  <!--[if mso]><div class="mso-container"><![endif]-->\n  <table role="presentation" style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;min-width: 320px;Margin: 0 auto;background-color: #FFFFFF;width:100%" cellpadding="0" cellspacing="0">\n  <tbody>\n  <tr style="vertical-align: top">\n    <td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top">\n    <!--[if (mso)|(IE)]><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="background-color: #FFFFFF;"><![endif]-->\n    \n  \n  \n<div class="u-row-container" style="padding: 0px;background-color: #FFFFFF">\n  <div class="u-row" style="margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: transparent;">\n    <div style="border-collapse: collapse;display: table;width: 100%;height: 100%;background-color: transparent;">\n      <!--[if (mso)|(IE)]><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: #FFFFFF;" align="center"><table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: transparent;"><![endif]-->\n      \n<!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]-->\n<div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;">\n  <div style="height: 100%;width: 100% !important;">\n  <!--[if (!mso)&(!IE)]><!--><div style="box-sizing: border-box; height: 100%; padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]-->\n  \n<table style="font-family:arial,helvetica,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">\n  <tbody>\n    <tr>\n      <td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:arial,helvetica,sans-serif;" align="left">\n        \n  <div style="font-size: 14px; line-height: 140%; text-align: left; word-wrap: break-word;">\n    <h1>Welcome!</h1><p>Start designing your email template here.</p><p>Use the <strong>Insert Tag</strong> button to add dynamic content.</p> {{subject}} {{addcc}}\n  </div>\n\n      </td>\n    </tr>\n  </tbody>\n</table>\n\n<table style="font-family:arial,helvetica,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">\n  <tbody>\n    <tr>\n      <td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:arial,helvetica,sans-serif;" align="left">\n        \n  <div style="font-size: 14px; line-height: 140%; text-align: left; word-wrap: break-word;">\n    <p style="line-height: 140%;">Eid Mubarak! </p>\n  </div>\n\n      </td>\n    </tr>\n  </tbody>\n</table>\n\n  <!--[if (!mso)&(!IE)]><!--></div><!--<![endif]-->\n  </div>\n</div>\n<!--[if (mso)|(IE)]></td><![endif]-->\n      <!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]-->\n    </div>\n  </div>\n  </div>\n  \n\n\n    <!--[if (mso)|(IE)]></td></tr></table><![endif]-->\n    </td>\n  </tr>\n  </tbody>\n  </table>\n  <!--[if mso]></div><![endif]-->\n  <!--[if IE]></div><![endif]-->\n</body>\n\n</html>\n
\.


--
-- Data for Name: faqs; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.faqs (id, question, answer, "order", is_active, created_at, updated_at) FROM stdin;
1	test	test	1	t	2025-10-09 09:33:32.591397	2025-10-09 09:37:08.051772
2	How to Shop	You can shop online only. 	2	t	2025-10-18 14:00:00.026076	2025-10-18 14:00:34.657694
\.


--
-- Data for Name: manufacturers; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.manufacturers (created_at, updated_at, id, name, is_approved, image, cover_image, slug, language, description, website, socials, is_active) FROM stdin;
2025-09-29 16:52:49.258806	2025-10-05 16:32:51.628464	5	Soul Food	f	{"id": 121, "filename": "soulfood-Logo.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/soulfood-Logo.webp", "size_mb": 0.01, "thumbnail": null, "media_type": "image"}	{"id": 122, "filename": "soulfoodbanner.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/soulfoodbanner.webp", "size_mb": 0.04, "thumbnail": null, "media_type": "image"}	soul-food	en	Soul Food Company	https://getsoulfood.com/	\N	t
2025-09-29 16:55:10.829101	2025-10-05 16:33:49.263672	6	PureLove	f	{"id": 123, "filename": "Purlove-Logo.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/Purlove-Logo.webp", "size_mb": 0, "thumbnail": null, "media_type": "image"}	{"id": 123, "filename": "Purlove-Logo.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/Purlove-Logo.webp", "size_mb": 0, "thumbnail": null, "media_type": "image"}	purelove	en	Pet Food	https://www.facebook.com/Purelovefoods/	\N	t
2025-09-29 17:08:29.0662	2025-10-05 16:29:50.887862	8	Abbott	f	{"id": 127, "filename": "abott-logo.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/abott-logo.webp", "size_mb": 0.01, "thumbnail": null, "media_type": "image"}	{"id": 128, "filename": "Aboott-logo.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/Aboott-logo.webp", "size_mb": 0, "thumbnail": null, "media_type": "image"}	abbott-1	en		https://www.abbott.com/	\N	t
2025-09-29 16:56:30.073024	2025-10-05 04:36:52.319195	7	Coca‑Cola	f	{"id": 125, "filename": "cocacola-logo.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/cocacola-logo.webp", "size_mb": 0.01, "thumbnail": null, "media_type": "image"}	{"id": 126, "filename": "Coca-Cola-logo.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/Coca-Cola-logo.webp", "size_mb": 0.07, "thumbnail": null, "media_type": "image"}	cocacola-1	en	Coca‑Cola 	https://www.coca-cola.com/pk/en	\N	t
2025-10-18 15:26:15.134321	\N	9	Dalda	f	{"id": 172, "filename": "Dalda-1.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/Dalda-1.webp", "size_mb": 0, "thumbnail": null, "media_type": "image"}	{"id": 172, "filename": "Dalda-1.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/Dalda-1.webp", "size_mb": 0, "thumbnail": null, "media_type": "image"}	dalda	en		https://www.daldafoods.com/	\N	t
2025-09-29 16:44:51.454001	2025-10-05 16:31:03.397582	4	Franitize	f	{"id": 118, "filename": "Franitize-logo.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/Franitize-logo.webp", "size_mb": 0.02, "thumbnail": null, "media_type": "image"}	{"id": 120, "filename": "coverimage.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/coverimage.webp", "size_mb": 0.02, "thumbnail": null, "media_type": "image"}	franitize-1	en	We touch your heart	https://www.facebook.com/franitize	\N	t
2024-01-12 19:13:13	2025-10-05 16:31:59.594772	1	Bata	f	{"id": 109, "filename": "Bata.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/Bata.webp", "size_mb": 0, "thumbnail": null, "media_type": "image"}	{"id": 110, "filename": "Bata-1.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/Bata-1.webp", "size_mb": 0, "thumbnail": null, "media_type": "image"}	bata	en	Bata Shoes	http://beta.com	[]	t
2025-10-18 15:29:42.880656	\N	11	Tullo	f	{"id": 175, "filename": "Tullo.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/Tullo.webp", "size_mb": 0.01, "thumbnail": null, "media_type": "image"}	null	tullo	en	Tullo	http://www.wazirali.com.pk/	\N	t
\.


--
-- Data for Name: media; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.media (created_at, updated_at, id, user_id, media_type, filename, extension, original, size_mb, thumbnail) FROM stdin;
2025-09-30 04:39:11.644288	\N	67	9	image	2.webp	.webp	/media/hamail@example.com/2.webp	0.02	/media/hamail@example.com/2_thumb.webp
2025-09-30 04:47:18.58674	\N	75	9	image	1.webp	.webp	/media/hamail@example.com/1.webp	0.02	\N
2025-09-30 06:53:31.796157	\N	88	9	image	Cold Pressed Flax Seed Oil.webp	.webp	/media/hamail@example.com/Cold Pressed Flax Seed Oil.webp	0.11	/media/hamail@example.com/Cold Pressed Flax Seed Oil_thumb.webp
2025-09-30 07:17:51.235157	\N	89	9	image	Apple Cider Vinegar.webp	.webp	/media/hamail@example.com/Apple Cider Vinegar.webp	0.04	/media/hamail@example.com/Apple Cider Vinegar_thumb.webp
2025-09-30 07:33:56.200596	\N	90	9	image	Dog-3KG.webp	.webp	/media/hamail@example.com/Dog-3KG.webp	0.07	/media/hamail@example.com/Dog-3KG_thumb.webp
2025-09-30 10:05:32.899192	\N	91	9	image	Cat_Chikcen.webp	.webp	/media/hamail@example.com/Cat_Chikcen.webp	0.06	/media/hamail@example.com/Cat_Chikcen_thumb.webp
2025-09-30 16:26:27.921296	\N	92	9	image	Screenshot 2025-01-19 185521.webp	.webp	/media/hamail@example.com/Screenshot 2025-01-19 185521.webp	0.08	\N
2025-10-01 06:02:47.58398	\N	93	8	image	download.webp	.webp	/media/admin@example.com/download.webp	0	\N
2025-10-01 06:08:49.207836	\N	94	9	image	categorylist.webp	.webp	/media/hamail@example.com/categorylist.webp	0.03	\N
2025-10-01 06:14:01.157481	\N	95	8	image	banner1.webp	.webp	/media/admin@example.com/banner1.webp	0.05	\N
2025-10-01 06:16:34.06154	\N	96	9	image	homepage.webp	.webp	/media/hamail@example.com/homepage.webp	0.14	/media/hamail@example.com/homepage_thumb.webp
2025-10-01 06:35:21.582377	\N	97	8	image	banner-1.webp	.webp	/media/admin@example.com/banner-1.webp	0.05	\N
2025-10-01 06:38:28.881865	\N	98	8	image	banner-11.webp	.webp	/media/admin@example.com/banner-11.webp	0.05	\N
2025-10-01 08:02:39.991915	\N	99	8	image	banner-111.webp	.webp	/media/admin@example.com/banner-111.webp	0.05	\N
2025-10-01 08:14:18.857929	\N	100	8	image	banner-12.webp	.webp	/media/admin@example.com/banner-12.webp	0.05	\N
2025-10-01 08:40:10.348938	\N	101	8	image	banner-121.webp	.webp	/media/admin@example.com/banner-121.webp	0.05	\N
2025-10-01 08:42:12.23542	\N	102	8	image	banner-122.webp	.webp	/media/admin@example.com/banner-122.webp	0.05	\N
2025-10-01 08:48:50.151621	\N	103	8	image	banner-0.webp	.webp	/media/admin@example.com/banner-0.webp	0.05	\N
2025-10-01 08:50:04.04179	\N	104	8	image	banner-01.webp	.webp	/media/admin@example.com/banner-01.webp	0.05	\N
2025-10-01 09:30:46.18854	\N	105	8	image	banner2.avif	.avif	/media/admin@example.com/banner2.avif	0.05	\N
2025-10-01 09:32:28.524606	\N	106	8	image	banner3.avif	.avif	/media/admin@example.com/banner3.avif	0.06	\N
2025-10-01 09:33:29.348084	\N	107	8	image	banner4.avif	.avif	/media/admin@example.com/banner4.avif	0.02	\N
2025-10-01 13:22:36.82355	\N	108	8	image	9899431.webp	.webp	/media/admin@example.com/9899431.webp	0.14	\N
2025-10-01 13:44:19.293545	\N	109	8	image	Bata.webp	.webp	/media/admin@example.com/Bata.webp	0	\N
2025-10-01 13:44:46.058872	\N	110	8	image	Bata-1.webp	.webp	/media/admin@example.com/Bata-1.webp	0	\N
2025-10-03 01:53:00.867129	\N	111	9	image	Apple Cider Vinegar1.webp	.webp	/media/hamail@example.com/Apple Cider Vinegar1.webp	0.04	/media/hamail@example.com/Apple Cider Vinegar1_thumb.webp
2025-10-04 07:26:37.335371	\N	115	8	image	banner42.avif	.avif	/media/admin@example.com/banner42.avif	0.02	\N
2025-10-04 07:51:00.491757	\N	116	9	image	Apple-Cider-Vinegar1.webp	.webp	/media/hamail@example.com/Apple-Cider-Vinegar1.webp	0.04	/media/hamail@example.com/Apple-Cider-Vinegar1_thumb.webp
2025-10-04 09:34:38.511337	\N	118	8	image	Franitize-logo.webp	.webp	/media/admin@example.com/Franitize-logo.webp	0.02	\N
2025-10-04 09:36:11.178787	\N	120	8	image	coverimage.webp	.webp	/media/admin@example.com/coverimage.webp	0.02	\N
2025-10-05 04:29:42.729736	\N	121	8	image	soulfood-Logo.webp	.webp	/media/admin@example.com/soulfood-Logo.webp	0.01	\N
2025-10-05 04:34:49.895497	\N	122	8	image	soulfoodbanner.webp	.webp	/media/admin@example.com/soulfoodbanner.webp	0.04	\N
2025-10-05 04:35:16.299618	\N	123	8	image	Purlove-Logo.webp	.webp	/media/admin@example.com/Purlove-Logo.webp	0	\N
2025-10-05 04:36:30.641524	\N	125	8	image	cocacola-logo.webp	.webp	/media/admin@example.com/cocacola-logo.webp	0.01	\N
2025-10-05 04:36:49.479441	\N	126	8	image	Coca-Cola-logo.webp	.webp	/media/admin@example.com/Coca-Cola-logo.webp	0.07	\N
2025-10-05 04:37:11.893063	\N	127	8	image	abott-logo.webp	.webp	/media/admin@example.com/abott-logo.webp	0.01	\N
2025-10-05 04:37:35.965366	\N	128	8	image	Aboott-logo.webp	.webp	/media/admin@example.com/Aboott-logo.webp	0	\N
2025-10-05 04:52:49.603283	\N	129	8	image	grocessory.webp	.webp	/media/admin@example.com/grocessory.webp	0	\N
2025-10-05 04:58:30.073854	\N	130	8	image	Beverages.webp	.webp	/media/admin@example.com/Beverages.webp	0	\N
2025-10-05 05:20:59.399158	\N	131	8	image	home-banner1.webp	.webp	/media/admin@example.com/home-banner1.webp	0.05	\N
2025-10-05 14:51:14.04849	\N	132	8	image	banner5.avif	.avif	/media/admin@example.com/banner5.avif	0.05	\N
2025-10-05 15:33:06.29189	\N	133	8	image	category-8.svg	.svg	/media/admin@example.com/category-8.svg	0.01	\N
2025-10-06 10:39:09.444621	\N	140	9	image	AppleCiderVinegar1.webp	.webp	/media/hamail@example.com/AppleCiderVinegar1.webp	0.04	/media/hamail@example.com/AppleCiderVinegar1_thumb.webp
2025-10-06 11:12:51.357922	\N	142	9	image	Chia-Seeds-215g.webp	.webp	/media/hamail@example.com/Chia-Seeds-215g.webp	0.06	/media/hamail@example.com/Chia-Seeds-215g_thumb.webp
2025-10-06 11:16:40.02083	\N	143	9	image	Cat-Chikcen.webp	.webp	/media/hamail@example.com/Cat-Chikcen.webp	0.06	/media/hamail@example.com/Cat-Chikcen_thumb.webp
2025-10-06 11:20:45.437185	\N	147	9	image	MospelcreamBottle.webp	.webp	/media/hamail@example.com/MospelcreamBottle.webp	0.01	/media/hamail@example.com/MospelcreamBottle_thumb.webp
2025-10-06 11:22:06.690937	\N	148	9	image	MospelFlipTop45ml.webp	.webp	/media/hamail@example.com/MospelFlipTop45ml.webp	0.01	/media/hamail@example.com/MospelFlipTop45ml_thumb.webp
2025-10-06 11:22:44.484146	\N	149	9	image	MospelSilk45ml.webp	.webp	/media/hamail@example.com/MospelSilk45ml.webp	0.01	/media/hamail@example.com/MospelSilk45ml_thumb.webp
2025-10-06 11:23:28.238283	\N	150	9	image	330ml.webp	.webp	/media/hamail@example.com/330ml.webp	0.01	/media/hamail@example.com/330ml_thumb.webp
2025-10-06 11:25:01.014099	\N	151	9	image	SugarCane.webp	.webp	/media/hamail@example.com/SugarCane.webp	0.06	/media/hamail@example.com/SugarCane_thumb.webp
2025-10-06 11:26:07.479575	\N	152	9	image	CocaCola12Can250ML.webp	.webp	/media/hamail@example.com/CocaCola12Can250ML.webp	0.04	/media/hamail@example.com/CocaCola12Can250ML_thumb.webp
2025-10-06 11:27:38.520971	\N	153	9	image	BottlePack15Ltr.webp	.webp	/media/hamail@example.com/BottlePack15Ltr.webp	0.07	/media/hamail@example.com/BottlePack15Ltr_thumb.webp
2025-10-06 12:18:05.131418	\N	154	8	image	pet-food_16779323.webp	.webp	/media/admin@example.com/pet-food_16779323.webp	0.01	\N
2025-10-06 12:36:16.949189	\N	155	8	image	Kitchen-Utensils.svg	.svg	/media/admin@example.com/Kitchen-Utensils.svg	0.05	\N
2025-10-06 12:43:06.683125	\N	156	8	image	cosmetics_499767.webp	.webp	/media/admin@example.com/cosmetics_499767.webp	0.01	\N
2025-10-11 09:52:08.080169	\N	158	9	image	pet-food_16779323.webp	.webp	/media/hamail@example.com/pet-food_16779323.webp	0.01	/media/hamail@example.com/pet-food_16779323_thumb.webp
2025-10-11 10:09:17.502969	\N	161	9	image	download.webp	.webp	/media/hamail@example.com/download.webp	0	/media/hamail@example.com/download_thumb.webp
2025-10-14 09:50:47.36664	\N	162	9	image	wireless.webp	.webp	/media/hamail@example.com/wireless.webp	0.02	/media/hamail@example.com/wireless_thumb.webp
2025-10-14 09:53:34.354476	\N	163	9	image	stainlesssteel.webp	.webp	/media/hamail@example.com/stainlesssteel.webp	0.04	/media/hamail@example.com/stainlesssteel_thumb.webp
2025-10-18 12:43:17.612575	\N	165	8	image	centered_logo.webp	.webp	/media/admin@example.com/centered_logo.webp	0.03	\N
2025-10-18 14:25:55.448951	\N	167	9	image	Picture12.webp	.webp	/media/hamail@example.com/Picture12.webp	0	/media/hamail@example.com/Picture12_thumb.webp
2025-10-18 14:27:15.931269	\N	168	9	image	Picture11.webp	.webp	/media/hamail@example.com/Picture11.webp	0.01	/media/hamail@example.com/Picture11_thumb.webp
2025-10-18 15:25:57.893463	\N	172	8	image	Dalda-1.webp	.webp	/media/admin@example.com/Dalda-1.webp	0	\N
2025-10-18 15:27:29.502951	\N	174	8	image	dasani_logo_677x180_v1.webp	.webp	/media/admin@example.com/dasani_logo_677x180_v1.webp	0.01	\N
2025-10-18 15:28:48.513324	\N	175	8	image	Tullo.webp	.webp	/media/admin@example.com/Tullo.webp	0.01	\N
2025-10-18 15:36:58.722456	\N	176	9	image	tullobanaspati1kg.webp	.webp	/media/hamail@example.com/tullobanaspati1kg.webp	0.02	/media/hamail@example.com/tullobanaspati1kg_thumb.webp
2025-10-18 15:38:19.029121	\N	177	9	image	tullocookingoil1kg.webp	.webp	/media/hamail@example.com/tullocookingoil1kg.webp	0.02	/media/hamail@example.com/tullocookingoil1kg_thumb.webp
2025-10-18 18:04:51.38434	\N	178	8	image	logo.webp	.webp	/media/admin@example.com/logo.webp	0.02	\N
\.


--
-- Data for Name: order_product; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.order_product (id, order_id, product_id, variation_option_id, order_quantity, unit_price, subtotal, admin_commission, deleted_at, created_at, updated_at, item_type, variation_data, variation_snapshot, shop_id) FROM stdin;
2	19	251	\N	1	310	310	37.20	\N	2025-10-08 10:08:14.83986	\N	SIMPLE	\N	\N	\N
3	19	241	\N	3	175	700	52.50	\N	2025-10-08 10:08:15.146078	\N	SIMPLE	\N	\N	\N
4	20	251	\N	1	310	310	37.20	\N	2025-10-08 10:49:44.400644	\N	SIMPLE	\N	\N	\N
5	20	241	\N	3	175	700	52.50	\N	2025-10-08 10:49:44.806462	\N	SIMPLE	\N	\N	\N
7	23	240	\N	5	200	1000	100.00	\N	2025-10-18 13:34:19.790444	\N	SIMPLE	null	null	3
8	23	241	\N	2	175	350	35.00	\N	2025-10-18 13:34:20.616274	\N	SIMPLE	null	null	3
9	24	248	\N	1	820	820	0.00	\N	2025-10-19 03:35:56.243325	\N	SIMPLE	\N	\N	\N
10	24	249	\N	1	700	700	0.00	\N	2025-10-19 03:35:56.243841	\N	SIMPLE	\N	\N	\N
11	25	248	\N	1	820	820	0.00	\N	2025-10-19 03:56:54.417383	\N	SIMPLE	\N	\N	\N
12	28	254	\N	1	69.99	69.99	0.00	\N	2025-10-19 04:31:55.739721	\N	SIMPLE	\N	\N	\N
13	29	245	\N	1	620	620	0.00	\N	2025-10-20 06:31:06.900184	\N	SIMPLE	\N	\N	\N
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.orders (id, tracking_number, customer_id, customer_contact, customer_name, amount, sales_tax, paid_total, total, cancelled_amount, admin_commission_amount, language, coupon_id, discount, payment_gateway, shipping_address, billing_address, logistics_provider, delivery_fee, delivery_time, fullfillment_id, assign_date, created_at, updated_at, order_status, payment_status) FROM stdin;
19	TRK-D0DFAED67B56	11	+923335755897	Ghalib Raza	1010	0	1010	1010	0.00	89.70	en	\N	0	string	{"country": "Pakistan", "city": "Islamabad", "state": "Federal", "area": "Sector F1", "zip_code": "44000", "street": "Rawalpindi"}	{"country": "Pakistan", "city": "Islamabad", "state": "Federal", "area": "Sector F1", "zip_code": "44000", "street": "Rawalpindi"}	0	0	Express Delivery	\N	\N	2025-10-08 10:08:12.800591	\N	order-pending	payment-pending
20	TRK-CAD5B4353736	11	+923335755897	Ghalib Raza	1010	0	1010	1010	0.00	89.70	en	\N	0	string	{"country": "Pakistan", "city": "Islamabad", "state": "Federal", "area": "Sector F1", "zip_code": "44000", "street": "Rawalpindi"}	{"country": "Pakistan", "city": "Islamabad", "state": "Federal", "area": "Sector F1", "zip_code": "44000", "street": "Rawalpindi"}	0	0	Express Delivery	\N	\N	2025-10-08 10:49:40.004036	\N	order-pending	payment-pending
23	TRK-A1345F5BE686	11	+923335755897	Ghalib Raza	1010	0	1350	1350	0.00	135.00	en	\N	0	cash-on-delivery	{"street": "Rawalpindi", "city": "Islamabad", "state": "Federal", "postal_code": null, "country": "Pakistan"}	{"street": "Rawalpindi", "city": "Islamabad", "state": "Federal", "postal_code": null, "country": "Pakistan"}	0	0	Express Delivery	\N	\N	2025-10-18 13:34:19.183993	\N	order-pending	payment-pending
24	TRK-8F5F71513A	\N	033000323232	john	1520	\N	\N	1520	0.00	0.00	en	\N	\N	\N	{"name": "john", "email": "john@example.com", "address": "123 street", "city": "lahore", "zip": "54000", "phone": "033000323232"}	{"name": "john", "email": "john@example.com", "address": "123 street", "city": "lahore", "zip": "54000", "phone": "033000323232"}	\N	\N	\N	\N	\N	2025-10-19 03:35:56.096545	\N	order-pending	payment-pending
25	TRK-D3AE96C7D1	\N	03305817334	Muhammad Hamail	820	\N	\N	820	0.00	0.00	en	\N	\N	\N	{"name": "Muhammad Hamail", "email": "mhamail1223@gmail.com", "address": "street 13", "city": "rawalpindi", "zip": "46000", "phone": "03305817334"}	{"name": "Muhammad Hamail", "email": "mhamail1223@gmail.com", "address": "street 13", "city": "rawalpindi", "zip": "46000", "phone": "03305817334"}	\N	\N	\N	\N	\N	2025-10-19 03:56:54.303932	\N	order-pending	payment-pending
28	TRK-6888386EFE	9	1234567895	hamail	69.99	\N	\N	69.99	0.00	0.00	en	\N	\N	\N	{"name": "hamail", "email": "hamail@example.com", "address": "street 13", "city": "rawalpindi", "zip": "46000", "phone": "1234567895"}	{"name": "hamail", "email": "hamail@example.com", "address": "street 13", "city": "rawalpindi", "zip": "46000", "phone": "1234567895"}	\N	\N	\N	\N	\N	2025-10-19 04:31:55.628173	\N	order-pending	payment-pending
29	TRK-1DE067F36F	14	923225000922	Abdullah Bin Qamar	620	\N	\N	620	0.00	0.00	en	\N	\N	\N	{"name": "Abdullah Bin Qamar", "email": "abdullah.qamar@gmail.com", "address": "39 Kahghan Road , F-8/3", "city": "Islamabad", "zip": "44000", "phone": "923225000922"}	{"name": "Abdullah Bin Qamar", "email": "abdullah.qamar@gmail.com", "address": "39 Kahghan Road , F-8/3", "city": "Islamabad", "zip": "44000", "phone": "923225000922"}	\N	\N	\N	\N	\N	2025-10-20 06:31:06.660544	\N	order-pending	payment-pending
\.


--
-- Data for Name: orders_status; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.orders_status (id, order_id, language, order_pending_date, order_processing_date, order_completed_date, order_refunded_date, order_failed_date, order_cancelled_date, order_at_local_facility_date, order_out_for_delivery_date, order_packed_date, order_at_distribution_center_date, created_at, updated_at) FROM stdin;
1	19	en	2025-10-08 15:08:15.146184	\N	\N	\N	\N	\N	\N	\N	\N	\N	2025-10-08 10:08:15.146232	\N
2	20	en	2025-10-08 15:49:44.806462	\N	\N	\N	\N	\N	\N	\N	\N	\N	2025-10-08 10:49:44.806462	\N
3	23	en	2025-10-18 18:34:20.886457	\N	\N	\N	\N	\N	\N	\N	\N	\N	2025-10-18 13:34:20.886457	\N
\.


--
-- Data for Name: product_import_history; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.product_import_history (id, filename, original_filename, file_size, total_records, successful_records, failed_records, status, import_errors, imported_products, shop_id, imported_by, created_at, completed_at) FROM stdin;
1	import_e6c36f78.xlsx	Book2.xlsx	9965	2	2	0	completed	[]	[{"product_id": 254, "name": "Wireless Bluetooth Headphones", "sku": "SK-HEADPHONE-001", "type": "simple", "sheet": "Sheet1", "row": 2}, {"product_id": 255, "name": "Stainless Steel Water Bottle", "sku": "SK-BOTTLE-001", "type": "simple", "sheet": "Sheet1", "row": 3}]	1	9	2025-10-12 17:40:16.638898	2025-10-12 17:40:32.557439
2	import_a9f2b5a5.xlsx	Tullo Products.xlsx	9724	4	2	1	completed	["Sheet 'Variable_Products': Error parsing variable product: Category 'Clothing' not found in database. Please create category first."]	[{"product_id": 258, "name": "Tullo Ghee", "sku": "SK-SIMPLE-001", "type": "simple", "sheet": "Simple_Products", "row": 2, "quantity": 150, "purchase_price": 500.0}, {"product_id": 259, "name": "Tullo Oil", "sku": "SK-SIMPLE-002", "type": "simple", "sheet": "Simple_Products", "row": 3, "quantity": 100, "purchase_price": 678.0}]	3	9	2025-10-18 15:34:50.699454	2025-10-18 15:35:01.807825
\.


--
-- Data for Name: product_purchase; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.product_purchase (created_at, updated_at, id, product_id, variation_option_id, quantity, purchase_date, price, sale_price, purchase_price, shop_id, min_price, max_price, purchase_type, transaction_type, reference_number, supplier_name, invoice_number, batch_number, expiry_date, notes, added_by, previous_stock, new_stock, transaction_details) FROM stdin;
2025-10-18 15:34:58.475548	\N	2	259	\N	100	2025-10-18 15:34:58.475637	\N	\N	678	3	\N	\N	DEBIT	STOCK_ADDITION	IMP-BA10BB39	Import System	\N	\N	\N	Initial stock added for new product: Tullo Oil via import	9	100	200	{"import_method": "excel_import", "original_filename": "Tullo Products.xlsx", "import_id": 2, "product_name": "Tullo Oil"}
2025-10-18 15:34:54.515834	\N	1	\N	\N	150	2025-10-18 15:34:54.515978	\N	\N	500	3	\N	\N	DEBIT	STOCK_ADDITION	IMP-F73C7D14	Import System	\N	\N	\N	Initial stock added for new product: Tullo Ghee via import	9	150	300	{"import_method": "excel_import", "original_filename": "Tullo Products.xlsx", "import_id": 2, "product_name": "Tullo Ghee"}
\.


--
-- Data for Name: product_purchase_variation_options; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.product_purchase_variation_options (created_at, updated_at, id, product_purchase_id, variation_options_id, price, sale_price, purchase_price, language, quantity, sku, product_id, purchase_date) FROM stdin;
\.


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.products (created_at, updated_at, id, name, slug, description, price, is_active, sale_price, purchase_price, language, min_price, max_price, sku, bar_code, quantity, in_stock, is_taxable, status, product_type, height, width, length, dimension_unit, image, video, deleted_at, is_digital, is_external, external_product_url, external_product_button_text, category_id, shop_id, unit, gallery, is_feature, manufacturer_id, meta_title, meta_description, warranty, return_policy, shipping_info, tags, weight, attributes, total_purchased_quantity, total_sold_quantity) FROM stdin;
2025-09-30 07:10:27.365422	2025-10-06 11:13:05.578399	248	Cold Pressed Flax Seed Oil	cold-pressed-flax-seed-oil	Cold Pressed Flax Seed Oil	900	t	820	650	en	900	900	PROD-100		150	t	f	PUBLISH	SIMPLE	\N	\N	\N		{"id": 142, "filename": "Chia-Seeds-215g.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/Chia-Seeds-215g.webp", "size_mb": 0.06, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/Chia-Seeds-215g_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	8	3	ml	null	f	5						["seed"]	0	\N	150	0
2025-09-30 07:18:56.082485	2025-10-06 11:17:43.355689	249	Apple Cider Vinegar	apple-cider-vinegar-1	Apple Cider Vinegar	700	t	0	0	en	700	700	PROD-10002		150	t	f	PUBLISH	SIMPLE	\N	\N	\N		{"id": 140, "filename": "AppleCiderVinegar1.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/AppleCiderVinegar1.webp", "size_mb": 0.04, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/AppleCiderVinegar1_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	8	3		null	\N	\N						["tag1", "tag2"]	0	\N	150	0
2025-09-30 07:36:33.223691	2025-10-06 11:19:44.900214	250	Dog & Puppy Food Feast Pack 3kg Beef Minis and 500g Premium chicken	dog-puppy-food-feast-pack-3kg-beef-minis-and-500g-premium-chicken-1	Dog & Puppy Food Feast Pack 3kg Beef Minis and 500g Premium chicken	2500	t	0	0	en	2500	2500	PROD-1002		150	t	f	PUBLISH	SIMPLE	\N	\N	\N		{"id": 90, "filename": "Dog-3KG.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/Dog-3KG.webp", "size_mb": 0.07, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/Dog-3KG_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	17	3	kg	null	t	6						["tag1", "tag2", "tag"]	0	\N	150	0
2025-09-30 10:06:59.633326	2025-10-06 11:16:58.554658	251	Meow For All Cats	meow-for-all-cats-1	PureLove Meow For All Cats 500G	310	t	330	300	en	310	310	PROD-101	123456789	150	t	f	PUBLISH	SIMPLE	\N	\N	\N	10x5x3 cm	{"id": 143, "filename": "Cat-Chikcen.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/Cat-Chikcen.webp", "size_mb": 0.06, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/Cat-Chikcen_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	15	3	g	null	\N	6	test	test	no warranty	30	free	["tag1", "tag2", "tag", "tagggg"]	0	\N	150	0
2025-10-12 17:40:26.242307	2025-10-14 09:51:40.955418	254	Wireless Bluetooth Headphones	wireless-bluetooth-headphones-1	High-quality wireless headphones with noise cancellation	79.99	t	69.99	35	en	79.99	79.99	SK-HEADPHONE-001	1234567890128	150	t	f	PUBLISH	SIMPLE	\N	\N	\N	10x5x3 cm	{"id": 162, "filename": "wireless.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/wireless.webp", "size_mb": 0.02, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/wireless_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	39	3	pcs	\N	\N	\N			no warranty	7 days return	Free Shipping over 3000	["electronics", "audio", "wireless", "bluetooth"]	0.3	null	150	0
2025-10-12 17:40:30.852624	2025-10-14 09:53:48.649483	255	Stainless Steel Water Bottle	stainless-steel-water-bottle-1	Eco-friendly stainless steel water bottle, keeps drinks cold for 24 hours	24.99	t	19.99	8.5	en	24.99	24.99	SK-BOTTLE-001	1234567890129	200	t	f	PUBLISH	SIMPLE	\N	\N	\N	10x5x3 cm	{"id": 163, "filename": "stainlesssteel.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/stainlesssteel.webp", "size_mb": 0.04, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/stainlesssteel_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	40	3	pcs	\N	\N	\N						["kitchen", "eco-friendly", "stainless-steel"]	0.4	null	200	0
2025-10-18 14:28:20.585303	\N	257	Calza Slippers	calza-slippers	Slippers	570	t	\N	\N	en	570	570	Slippers-001		231	t	f	PUBLISH	VARIABLE	\N	\N	\N		{"id": 167, "filename": "Picture12.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/Picture12.webp", "size_mb": 0, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/Picture12_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	30	3		null	f	1						[]	\N	[{"id": 6, "name": "Size", "values": [{"id": 7, "value": "Small", "meta": "S"}, {"id": 8, "value": "Medium", "meta": "M"}, {"id": 9, "value": "Large", "meta": "L"}, {"id": 10, "value": "Extra Large", "meta": "XL"}, {"id": 11, "value": "Double Extra Large", "meta": "XXL"}], "selected_values": [7, 8], "is_visible": true, "is_variation": true}, {"id": 5, "name": "color", "values": [{"id": 5, "value": "Red", "meta": "#FF0000"}, {"id": 6, "value": "Green", "meta": "#008000"}], "selected_values": [5, 6], "is_visible": true, "is_variation": true}]	0	0
2025-10-18 15:34:57.232514	2025-10-18 15:38:34.560586	259	Tullo Oil	tullo-oil-1	Tullo Oil	980	t	980	678	en	980	980	SK-SIMPLE-002	1234567890123	100	t	f	PUBLISH	SIMPLE	\N	\N	\N		{"id": 177, "filename": "tullocookingoil1kg.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/tullocookingoil1kg.webp", "size_mb": 0.02, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/tullocookingoil1kg_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	8	3	ltr	\N	\N	11						["oil", "ghee", "cooking oil"]	1	null	100	0
2025-09-29 17:31:27.048617	2025-10-06 11:21:12.200551	241	Mospel Cream 45ml	mospel-cream-45ml-1	Mospel Cream 45ml	175	t	0	0	en	175	175	PROD-10003		148	t	f	PUBLISH	SIMPLE	\N	\N	\N		{"id": 147, "filename": "MospelcreamBottle.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/MospelcreamBottle.webp", "size_mb": 0.01, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/MospelcreamBottle_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	22	3	ml	null	t	8						["tag1", "tag2", "tag"]	0	\N	150	2
2025-09-29 17:28:03.589737	2025-10-06 11:22:24.580222	240	Mospel FlipTop 45ml	mospel-fliptop-45ml	Mospel FlipTop 45ml	200	t	0	0	en	200	200	prod-009		145	t	f	PUBLISH	SIMPLE	\N	\N	\N		{"id": 148, "filename": "MospelFlipTop45ml.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/MospelFlipTop45ml.webp", "size_mb": 0.01, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/MospelFlipTop45ml_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	22	3	ml	null	t	8						["tag1", "tag2", "tag"]	0	\N	150	5
2025-09-29 17:33:09.533812	2025-10-06 11:23:02.629458	242	Mospel Silk 45ml	mospel-silk-45ml-1	Mospel Silk 45ml	200	t	0	0	en	200	200	PROD-10006		150	t	f	PUBLISH	SIMPLE	\N	\N	\N		{"id": 149, "filename": "MospelSilk45ml.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/MospelSilk45ml.webp", "size_mb": 0.01, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/MospelSilk45ml_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	22	3	ml	null	\N	8						["tag1", "tag2", "tag"]	0	\N	150	0
2025-09-29 17:35:12.58402	2025-10-06 11:26:41.250492	243	Coca Cola 12 Can 250ML	coca-cola-12-can-250ml-1	Coca Cola 12 Can 250ML	600	t	600	500	en	600	600	PROD-100900		150	t	f	PUBLISH	SIMPLE	\N	\N	\N		{"id": 152, "filename": "CocaCola12Can250ML.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/CocaCola12Can250ML.webp", "size_mb": 0.04, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/CocaCola12Can250ML_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	12	3	ml	null	t	7						["tag1", "tag2"]	250	\N	150	0
2025-09-29 17:38:05.177847	2025-10-06 11:24:19.27282	244	Coca Cola 12 Can 330ML	coca-cola-12-can-330ml	Coca Cola 12 Can 330ML	800	t	678	500	en	800	800	PROD-10009		150	t	f	PUBLISH	SIMPLE	\N	\N	\N		{"id": 150, "filename": "330ml.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/330ml.webp", "size_mb": 0.01, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/330ml_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	12	3	ml	null	\N	7						["tag1", "tag2"]	330	\N	150	0
2025-09-29 17:39:51.544582	2025-10-06 11:28:10.637668	245	Coca Cola 6 Bottle Pack 1.5 Ltr	coca-cola-6-bottle-pack-1-5-ltr-1	Coca Cola 6 Bottle Pack 1.5 Ltr	650	t	620	560	en	650	650	PROD-1007878		150	t	f	PUBLISH	SIMPLE	\N	\N	\N		{"id": 153, "filename": "BottlePack15Ltr.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/BottlePack15Ltr.webp", "size_mb": 0.07, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/BottlePack15Ltr_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	12	3	Ltr	null	t	7						["tag1", "tag2"]	1.5	\N	150	0
2025-09-30 02:00:56.2517	2025-10-06 11:25:14.946709	246	Raw Cane Sugar	raw-cane-sugar	SoulFood - Raw Cane Sugar	700	t	0	0	en	700	700	PROD-100110		150	t	f	PUBLISH	SIMPLE	\N	\N	\N		{"id": 151, "filename": "SugarCane.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/SugarCane.webp", "size_mb": 0.06, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/SugarCane_thumb.webp", "media_type": "image"}	null	\N	f	f	\N	\N	20	3		null	\N	5						["tag1", "tag2", "tag"]	0	\N	150	0
2025-09-30 02:03:24.232971	\N	247	Chia Seeds	chia-seeds-1	Chia Seeds 215g	2000	t	\N	\N	en	2000	2000	\N	\N	150	t	f	PUBLISH	SIMPLE	\N	\N	\N	\N	{"filename": "Chia Seeds 215g.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/Chia Seeds 215g.webp", "size_mb": 0.06, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/Chia Seeds 215g_thumb.webp"}	null	\N	f	f	\N	\N	19	3	g	null	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	150	0
\.


--
-- Data for Name: return_items; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.return_items (created_at, updated_at, id, return_request_id, order_item_id, product_id, variation_option_id, quantity, unit_price, refund_amount) FROM stdin;
\.


--
-- Data for Name: return_requests; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.return_requests (created_at, updated_at, id, order_id, user_id, return_type, reason, status, refund_amount, refund_status, wallet_credit_id, transfer_eligible_at, transferred_at, admin_notes, rejected_reason) FROM stdin;
\.


--
-- Data for Name: reviews; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.reviews (id, order_id, user_id, shop_id, product_id, variation_option_id, comment, rating, photos, deleted_at, created_at, updated_at) FROM stdin;
1	19	11	3	251	\N	this is my first comments	5	{}	\N	2025-10-09 06:46:45.757191	\N
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.roles (created_at, updated_at, id, name, description, permissions, is_active, user_id, slug) FROM stdin;
2025-09-15 07:53:05.68345	\N	20	root	\N	["all","system:*"]	t	8	root-20
2025-09-15 07:53:05.683961	\N	21	shop_admin	\N	["shop_admin","role","system:*"]	t	8	shop_admin-21
2025-10-14 11:55:13.670715	\N	22	Fulfillment	Delivery boy get their assign order pick and deliver to the customer	["order", "order-update"]	t	8	fulfillment
\.


--
-- Data for Name: settings; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.settings (created_at, updated_at, id, options, language) FROM stdin;
2025-10-17 18:41:16.967068	\N	3	{"seo": {"ogImage": null, "ogTitle": null, "metaTags": null, "metaTitle": null, "canonicalUrl": null, "ogDescription": null, "twitterHandle": null, "metaDescription": null, "twitterCardType": null}, "logo": {"id": 165, "filename": "centered_logo.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/centered_logo.webp", "size_mb": 0.03, "thumbnail": null, "media_type": "image"}, "collapseLogo": {"id": 165, "filename": "centered_logo.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/centered_logo.webp", "size_mb": 0.03, "thumbnail": null, "media_type": "image"}, "useOtp": false, "currency": "Rs.", "taxClass": "1", "siteTitle": "Ghartak", "deliveryTime": [{"title": "Express Delivery", "description": "90 min express delivery"}, {"title": "Morning", "description": "8.00 AM - 11.00 AM"}, {"title": "Noon", "description": "11.00 AM - 2.00 PM"}, {"title": "Afternoon", "description": "2.00 PM - 5.00 PM"}, {"title": "Evening", "description": "5.00 PM - 8.00 PM"}], "freeShipping": true, "signupPoints": 100, "siteSubtitle": "Your next ecommerce", "useGoogleMap": false, "shippingClass": "4", "contactDetails": {"contact": "+923335755897", "socials": [{"url": "https://www.facebook.com/ghartak", "icon": "FacebookIcon"}, {"url": "https://twitter.com/ghartak", "icon": "TwitterIcon"}, {"url": "https://www.instagram.com/ghartak", "icon": "InstagramIcon"}], "website": "https://ctspk.com", "emailAddress": "admin@example.com", "location": {"lat": 42.9585979, "lng": -76.9087202, "zip": "44000", "city": "Islamabad", "state": "Capital", "country": "Pakistan", "formattedAddress": "House # 5"}}, "paymentGateway": [{"name": "Easypaisa", "title": "Easypaisa"}, {"name": "Jazzcash", "title": "Jazzcash"}, {"name": "Card", "title": "Card"}], "currencyOptions": {"formation": "en-US", "fractions": 2}, "enableCoupons": false, "isMultiCommissionRate": false, "enableReviewPopup": false, "isProductReview": false, "useEnableGateway": true, "useCashOnDelivery": true, "freeShippingAmount": "3000", "minimumOrderAmount": "3000", "useMustVerifyEmail": false, "maximumQuestionLimit": 5, "currencyToWalletRatio": 3, "enableEmailForDigitalProduct": false, "StripeCardOnly": false, "guestCheckout": true, "server_info": {"upload_max_filesize": 2048, "memory_limit": "128M", "max_execution_time": "0", "max_input_time": "0", "post_max_size": 8192}, "useAi": false, "defaultAi": "openai", "maxShopDistance": 1000, "siteLink": "https://ghartak.com", "copyrightText": "Copyright \\u00a9 GHARTAK. All rights reserved worldwide.", "externalText": "Versel", "externalLink": "https://ctspk-frontend.vercel.app/", "reviewSystem": {"value": "review_single_time", "name": "Give purchased product a review only for one time. (By default)"}, "smsEvent": {"admin": {"statusChangeOrder": false, "refundOrder": false, "paymentOrder": false}, "vendor": {"statusChangeOrder": false, "paymentOrder": false, "refundOrder": false}, "customer": {"statusChangeOrder": false, "refundOrder": false, "paymentOrder": false}}, "emailEvent": {"admin": {"statusChangeOrder": false, "refundOrder": false, "paymentOrder": false}, "vendor": {"createQuestion": false, "statusChangeOrder": false, "refundOrder": false, "paymentOrder": false, "createReview": false}, "customer": {"statusChangeOrder": false, "refundOrder": false, "paymentOrder": false, "answerQuestion": false}}, "pushNotification": {"all": {"order": false, "message": false, "storeNotice": false}}, "isUnderMaintenance": true, "maintenance": {"title": "Site is under Maintenance", "buttonTitleOne": "Notify Me", "newsLetterTitle": "Subscribe Newsletter", "buttonTitleTwo": "Contact Us", "contactUsTitle": "Contact Us", "aboutUsTitle": "About Us", "isOverlayColor": false, "overlayColor": null, "overlayColorRange": null, "description": "We are currently undergoing essential maintenance to elevate your browsing experience. Our team is working diligently to implement improvements that will bring you an even more seamless and enjoyable interaction with our site. During this period, you may experience temporary inconveniences. We appreciate your patience and understanding. Thank you for being a part of our community, and we look forward to unveiling the enhanced features and content soon.", "newsLetterDescription": "Stay in the loop! Subscribe to our newsletter for exclusive deals and the latest trends delivered straight to your inbox. Elevate your shopping experience with insider access.", "aboutUsDescription": "Welcome to Pickbazar, your go-to destination for curated excellence. Discover a fusion of style, quality, and affordability in every click. Join our community and elevate your shopping experience with us!", "image": {"id": 178, "filename": "logo.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/admin@example.com/logo.webp", "size_mb": 0.02, "thumbnail": null, "media_type": "image"}, "start": "2024-09-13T05:29:19.577804Z", "until": "2024-09-14T05:29:19.577819Z"}, "isPromoPopUp": true, "promoPopup": {"image": {"id": 1793, "original": "https://pickbazarlaravel.s3.ap-southeast-1.amazonaws.com/1791/pickbazar02.png", "file_name": "pickbazar02.png", "thumbnail": "https://pickbazarlaravel.s3.ap-southeast-1.amazonaws.com/1791/conversions/pickbazar02-thumbnail.jpg"}, "title": "Get 25% Discount", "popUpDelay": 5000, "description": "Subscribe to the mailing list to receive updates on new arrivals, special offers and our promotions.", "popUpNotShow": {"title": "Don't show this popup again", "popUpExpiredIn": 7}, "isPopUpNotShow": true, "popUpExpiredIn": 1}, "app_settings": {"trust": true, "last_checking_time": "2025-06-27T09:20:17.780105Z"}}	en
\.


--
-- Data for Name: shipping_classes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.shipping_classes (created_at, updated_at, id, name, slug, amount, is_global, is_active, language, type) FROM stdin;
2025-10-03 02:04:51.950765	2025-10-03 02:48:47.85295	4	Free Shipping	free-shipping	0	t	t	en	FIXED
2025-10-18 13:54:38.545891	\N	5	Cash on Delivery	cash-on-delivery	5	f	t	en	PERCENTAGE
\.


--
-- Data for Name: shop_earnings; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.shop_earnings (created_at, updated_at, id, shop_id, order_id, order_amount, admin_commission, shop_earning, is_settled, settled_at, order_product_id) FROM stdin;
\.


--
-- Data for Name: shop_withdraw_requests; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.shop_withdraw_requests (created_at, updated_at, id, shop_id, amount, admin_commission, net_amount, status, payment_method, bank_name, account_number, account_holder_name, ifsc_code, cash_handled_by, cash_payment_date, processed_by, processed_at, rejection_reason) FROM stdin;
\.


--
-- Data for Name: shops; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.shops (created_at, updated_at, id, owner_id, name, slug, description, cover_image, logo, is_active, address, settings, notifications) FROM stdin;
2025-09-29 15:54:37.035647	2025-10-01 14:06:27.722202	3	9	D.Watson Cash & Carry	d-watson-cash-carry		null	{"size_mb": 0, "filename": "images.webp", "original": "https://api.ctspk.com/media/hamail@example.com/images.webp", "extension": ".webp", "thumbnail": null}	t	{"zip": "44000", "area": "Blue Area", "city": "Islamabad", "state": "Federal", "country": "Pakistan", "street_address": "Din Pavilion, F-7"}	null	null
2025-09-15 14:15:50.715483	2025-10-18 13:43:23.771832	1	9	Hatim Super Market	hatim-super-market	This is Hatim Super Market	{"id": "1941", "original": "https://api.ctspk.com/public/storage/1930/Hatim-Cover-Img.jpg", "thumbnail": "https://api.ctspk.com/public/storage/1930/conversions/Hatim-Cover-Img-thumbnail.jpg"}	{"id": "1940", "original": "https://api.ctspk.com/public/storage/1929/Hatim-Logo.jpg", "thumbnail": "https://api.ctspk.com/public/storage/1929/conversions/Hatim-Logo-thumbnail.jpg"}	t	{"zip": "44000", "area": "Sector F1", "city": "Islamabad", "state": "Federal", "country": "Pakistan", "street_address": "Islamabad"}	{"contact": "03225000999", "socials": [], "website": "ere", "location": [], "notifications": []}	null
\.


--
-- Data for Name: tax_classes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.tax_classes (created_at, updated_at, id, name, country, state, zip, city, rate, is_global, priority, on_shipping) FROM stdin;
2025-10-18 11:53:46.759711	\N	1	Global	string	string	string	string	16	t	1	t
\.


--
-- Data for Name: user_roles; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_roles (created_at, updated_at, id, user_id, role_id) FROM stdin;
2025-09-15 07:53:05.791722	\N	6	8	20
2025-09-15 14:15:53.604326	\N	7	9	21
2025-09-29 15:48:01.854731	\N	8	8	21
2025-10-14 13:32:39.311913	\N	9	18	22
\.


--
-- Data for Name: user_shop; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_shop (created_at, updated_at, id, user_id, shop_id) FROM stdin;
2025-09-16 07:01:19.589328	\N	4	10	1
\.


--
-- Data for Name: user_wallets; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_wallets (created_at, updated_at, id, user_id, balance, total_credited, total_debited) FROM stdin;
2025-10-17 10:19:53.432439	\N	1	11	0	0	0
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.users (created_at, updated_at, id, name, email, phone_no, email_verified_at, password, remember_token, is_active, is_root) FROM stdin;
2025-09-16 04:08:48.402177	\N	10	user staff	test@example.com	123	\N	$2b$12$FIG9NosDnVkJeAlhHogAD.GJ7E4IE8MEsF8ghzWxzOpt.UJNbGx3i	\N	t	f
2025-09-18 05:23:02.610775	\N	11	Ghalib Raza	rurazza@example.com	923058765040	\N	$2b$12$narD1pYGjngU/2kCw7okseyt9WtqFffNxomWTzsHPhtZ.WY18.FAC	\N	t	f
2025-09-15 07:53:03.864063	\N	8	admin	admin@example.com	123	\N	$2b$12$narD1pYGjngU/2kCw7okseyt9WtqFffNxomWTzsHPhtZ.WY18.FAC	\N	t	t
2025-09-28 14:07:53.689356	\N	12	Ghalib Raza	ghalib@example.com	03335755897	\N	$2b$12$DZNrn.kkuePj/DXca.WMQu9cRq7aPTGNFjzv6/4A3o88xanLB26p6	\N	t	f
2025-10-04 09:10:57.478152	\N	14	Abdullah Bin Qamar	abdullah.qamar@gmail.com	923225000922	\N	$2b$12$HTjQ4huEw3a6.OoMmsYox.Ul1QMKKQSH0IiGaFWdnoPzkuRNJ6Eoy	\N	t	f
2025-10-13 18:36:56.841483	\N	15	tayyab	tayyab@example.com	03315287615	\N	$2b$12$Wt3pYlU5E/tDiPbj9EIqYugJ0LinQMQDCDlinsiigXzz37cWfrX/y	\N	t	f
2025-10-14 13:32:38.814388	\N	18	MUDASSIR KAZMI	fullfilment@example.com	+923140835103	\N	$2b$12$j1Pq57MyVt55oL6.14b85uUqKwZccS/XtqN0NMGtiSjFQLThoxCom	\N	t	f
2025-09-15 13:50:10.652155	2025-10-18 07:30:15.79903	9	hamail	hamail@example.com	123	\N	$2b$12$x/8PH9lrdwR.OBTgna0a1eCo8XaYWoN2kvlz0M4Nym/Of5QbgvGYa	\N	t	f
\.


--
-- Data for Name: variation_options; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.variation_options (id, title, image, price, sale_price, purchase_price, language, quantity, is_disable, sku, options, product_id, created_at, updated_at, is_digital, bar_code, is_active) FROM stdin;
3	Size: Small - color: Red	{"id": 167, "filename": "Picture12.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/Picture12.webp", "size_mb": 0, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/Picture12_thumb.webp", "media_type": "image"}	570.0	\N	4000	en	120	f	VAR-2	{"Size": "Small", "color": "Red"}	257	2025-10-18 14:28:21.849138	\N	f	BC-1760797597734-2	t
4	Size: Small - color: Green	{"id": 168, "filename": "Picture11.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/Picture11.webp", "size_mb": 0.01, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/Picture11_thumb.webp", "media_type": "image"}	570.0	\N	400	en	15	f	VAR-3	{"Size": "Small", "color": "Green"}	257	2025-10-18 14:28:21.849616	\N	f	BC-1760797597734-3	t
5	Size: Medium - color: Red	{"id": 167, "filename": "Picture12.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/Picture12.webp", "size_mb": 0, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/Picture12_thumb.webp", "media_type": "image"}	570.0	\N	400	en	41	f	VAR-4	{"Size": "Medium", "color": "Red"}	257	2025-10-18 14:28:21.849784	\N	f	BC-1760797597734-4	t
6	Size: Medium - color: Green	{"id": 168, "filename": "Picture11.webp", "extension": ".webp", "original": "https://api.ctspk.com/media/hamail@example.com/Picture11.webp", "size_mb": 0.01, "thumbnail": "https://api.ctspk.com/media/hamail@example.com/Picture11_thumb.webp", "media_type": "image"}	570.0	\N	399.98	en	55	f	VAR-5	{"Size": "Medium", "color": "Green"}	257	2025-10-18 14:28:21.849933	\N	f	BC-1760797597734-5	t
\.


--
-- Data for Name: wallet_transactions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.wallet_transactions (created_at, updated_at, id, user_id, amount, transaction_type, balance_after, description, is_refund, transfer_eligible_at, transferred_to_bank, transferred_at, return_request_id) FROM stdin;
\.


--
-- Data for Name: wishlists; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.wishlists (id, user_id, product_id, variation_option_id, created_at, updated_at) FROM stdin;
2	11	251	\N	2025-10-09 06:42:11.291523	\N
\.


--
-- Name: address_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.address_id_seq', 2, true);


--
-- Name: attribute_product_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.attribute_product_id_seq', 2, true);


--
-- Name: attribute_values_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.attribute_values_id_seq', 12, true);


--
-- Name: attributes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.attributes_id_seq', 6, true);


--
-- Name: banners_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.banners_id_seq', 6, true);


--
-- Name: carts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.carts_id_seq', 32, true);


--
-- Name: categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.categories_id_seq', 40, true);


--
-- Name: coupons_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.coupons_id_seq', 3, true);


--
-- Name: email_template_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.email_template_id_seq', 6, true);


--
-- Name: faqs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.faqs_id_seq', 2, true);


--
-- Name: manufacturers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.manufacturers_id_seq', 11, true);


--
-- Name: media_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.media_id_seq', 178, true);


--
-- Name: order_product_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.order_product_id_seq', 13, true);


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.orders_id_seq', 29, true);


--
-- Name: orders_status_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.orders_status_id_seq', 3, true);


--
-- Name: product_import_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.product_import_history_id_seq', 2, true);


--
-- Name: product_purchase_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.product_purchase_id_seq', 2, true);


--
-- Name: product_purchase_variation_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.product_purchase_variation_options_id_seq', 1, false);


--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.products_id_seq', 259, true);


--
-- Name: return_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.return_items_id_seq', 1, false);


--
-- Name: return_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.return_requests_id_seq', 1, false);


--
-- Name: reviews_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.reviews_id_seq', 1, true);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.roles_id_seq', 22, true);


--
-- Name: settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.settings_id_seq', 3, true);


--
-- Name: shipping_classes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.shipping_classes_id_seq', 5, true);


--
-- Name: shop_earnings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.shop_earnings_id_seq', 1, false);


--
-- Name: shop_withdraw_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.shop_withdraw_requests_id_seq', 1, false);


--
-- Name: shops_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.shops_id_seq', 3, true);


--
-- Name: tax_classes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.tax_classes_id_seq', 1, true);


--
-- Name: user_roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.user_roles_id_seq', 9, true);


--
-- Name: user_shop_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.user_shop_id_seq', 4, true);


--
-- Name: user_wallets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.user_wallets_id_seq', 1, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.users_id_seq', 18, true);


--
-- Name: variation_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.variation_options_id_seq', 6, true);


--
-- Name: wallet_transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.wallet_transactions_id_seq', 1, false);


--
-- Name: wishlists_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.wishlists_id_seq', 2, true);


--
-- Name: address address_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.address
    ADD CONSTRAINT address_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: attribute_product attribute_product_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.attribute_product
    ADD CONSTRAINT attribute_product_pkey PRIMARY KEY (id);


--
-- Name: attribute_values attribute_values_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.attribute_values
    ADD CONSTRAINT attribute_values_pkey PRIMARY KEY (id);


--
-- Name: attributes attributes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.attributes
    ADD CONSTRAINT attributes_pkey PRIMARY KEY (id);


--
-- Name: banners banners_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.banners
    ADD CONSTRAINT banners_pkey PRIMARY KEY (id);


--
-- Name: carts carts_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.carts
    ADD CONSTRAINT carts_pkey PRIMARY KEY (id);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: coupons coupons_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.coupons
    ADD CONSTRAINT coupons_pkey PRIMARY KEY (id);


--
-- Name: email_template email_template_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.email_template
    ADD CONSTRAINT email_template_pkey PRIMARY KEY (id);


--
-- Name: faqs faqs_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.faqs
    ADD CONSTRAINT faqs_pkey PRIMARY KEY (id);


--
-- Name: manufacturers manufacturers_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.manufacturers
    ADD CONSTRAINT manufacturers_pkey PRIMARY KEY (id);


--
-- Name: media media_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.media
    ADD CONSTRAINT media_pkey PRIMARY KEY (id);


--
-- Name: order_product order_product_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.order_product
    ADD CONSTRAINT order_product_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: orders_status orders_status_order_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders_status
    ADD CONSTRAINT orders_status_order_id_key UNIQUE (order_id);


--
-- Name: orders_status orders_status_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders_status
    ADD CONSTRAINT orders_status_pkey PRIMARY KEY (id);


--
-- Name: orders orders_tracking_number_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_tracking_number_key UNIQUE (tracking_number);


--
-- Name: product_import_history product_import_history_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_import_history
    ADD CONSTRAINT product_import_history_pkey PRIMARY KEY (id);


--
-- Name: product_purchase product_purchase_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_purchase
    ADD CONSTRAINT product_purchase_pkey PRIMARY KEY (id);


--
-- Name: product_purchase product_purchase_reference_number_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_purchase
    ADD CONSTRAINT product_purchase_reference_number_key UNIQUE (reference_number);


--
-- Name: product_purchase_variation_options product_purchase_variation_options_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_purchase_variation_options
    ADD CONSTRAINT product_purchase_variation_options_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: return_items return_items_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.return_items
    ADD CONSTRAINT return_items_pkey PRIMARY KEY (id);


--
-- Name: return_requests return_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.return_requests
    ADD CONSTRAINT return_requests_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: roles roles_name_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (id);


--
-- Name: shipping_classes shipping_classes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shipping_classes
    ADD CONSTRAINT shipping_classes_pkey PRIMARY KEY (id);


--
-- Name: shop_earnings shop_earnings_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shop_earnings
    ADD CONSTRAINT shop_earnings_pkey PRIMARY KEY (id);


--
-- Name: shop_withdraw_requests shop_withdraw_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shop_withdraw_requests
    ADD CONSTRAINT shop_withdraw_requests_pkey PRIMARY KEY (id);


--
-- Name: shops shops_name_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shops
    ADD CONSTRAINT shops_name_key UNIQUE (name);


--
-- Name: shops shops_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shops
    ADD CONSTRAINT shops_pkey PRIMARY KEY (id);


--
-- Name: tax_classes tax_classes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.tax_classes
    ADD CONSTRAINT tax_classes_pkey PRIMARY KEY (id);


--
-- Name: media uix_user_file; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.media
    ADD CONSTRAINT uix_user_file UNIQUE (user_id, filename);


--
-- Name: carts uix_user_product; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.carts
    ADD CONSTRAINT uix_user_product UNIQUE (user_id, product_id);


--
-- Name: user_roles user_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_pkey PRIMARY KEY (id);


--
-- Name: user_shop user_shop_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_shop
    ADD CONSTRAINT user_shop_pkey PRIMARY KEY (id);


--
-- Name: user_wallets user_wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_wallets
    ADD CONSTRAINT user_wallets_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: variation_options variation_options_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.variation_options
    ADD CONSTRAINT variation_options_pkey PRIMARY KEY (id);


--
-- Name: wallet_transactions wallet_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallet_transactions
    ADD CONSTRAINT wallet_transactions_pkey PRIMARY KEY (id);


--
-- Name: wishlists wishlists_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wishlists
    ADD CONSTRAINT wishlists_pkey PRIMARY KEY (id);


--
-- Name: ix_banners_slug; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_banners_slug ON public.banners USING btree (slug);


--
-- Name: ix_categories_root_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_categories_root_id ON public.categories USING btree (root_id);


--
-- Name: ix_categories_slug; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_categories_slug ON public.categories USING btree (slug);


--
-- Name: ix_coupons_code; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_coupons_code ON public.coupons USING btree (code);


--
-- Name: ix_email_template_slug; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_email_template_slug ON public.email_template USING btree (slug);


--
-- Name: ix_emails_slug; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_emails_slug ON public.email_template USING btree (slug);


--
-- Name: ix_faqs_is_active; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_faqs_is_active ON public.faqs USING btree (is_active);


--
-- Name: ix_faqs_order; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_faqs_order ON public.faqs USING btree ("order");


--
-- Name: ix_manufacturers_slug; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_manufacturers_slug ON public.manufacturers USING btree (slug);


--
-- Name: ix_products_category_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_products_category_id ON public.products USING btree (category_id);


--
-- Name: ix_products_manufacturer_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_products_manufacturer_id ON public.products USING btree (manufacturer_id);


--
-- Name: ix_products_shop_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_products_shop_id ON public.products USING btree (shop_id);


--
-- Name: ix_products_slug; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_products_slug ON public.products USING btree (slug);


--
-- Name: ix_return_items_order_item_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_return_items_order_item_id ON public.return_items USING btree (order_item_id);


--
-- Name: ix_return_items_product_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_return_items_product_id ON public.return_items USING btree (product_id);


--
-- Name: ix_return_items_return_request_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_return_items_return_request_id ON public.return_items USING btree (return_request_id);


--
-- Name: ix_return_requests_order_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_return_requests_order_id ON public.return_requests USING btree (order_id);


--
-- Name: ix_return_requests_refund_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_return_requests_refund_status ON public.return_requests USING btree (refund_status);


--
-- Name: ix_return_requests_return_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_return_requests_return_type ON public.return_requests USING btree (return_type);


--
-- Name: ix_return_requests_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_return_requests_status ON public.return_requests USING btree (status);


--
-- Name: ix_return_requests_transfer_eligible_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_return_requests_transfer_eligible_at ON public.return_requests USING btree (transfer_eligible_at);


--
-- Name: ix_return_requests_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_return_requests_user_id ON public.return_requests USING btree (user_id);


--
-- Name: ix_reviews_order_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_reviews_order_id ON public.reviews USING btree (order_id);


--
-- Name: ix_reviews_product_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_reviews_product_id ON public.reviews USING btree (product_id);


--
-- Name: ix_reviews_shop_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_reviews_shop_id ON public.reviews USING btree (shop_id);


--
-- Name: ix_reviews_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_reviews_user_id ON public.reviews USING btree (user_id);


--
-- Name: ix_reviews_variation_option_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_reviews_variation_option_id ON public.reviews USING btree (variation_option_id);


--
-- Name: ix_roles_slug; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_roles_slug ON public.roles USING btree (slug);


--
-- Name: ix_settings_language; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_settings_language ON public.settings USING btree (language);


--
-- Name: ix_shipping_classes_slug; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_shipping_classes_slug ON public.shipping_classes USING btree (slug);


--
-- Name: ix_shop_earnings_order_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_shop_earnings_order_id ON public.shop_earnings USING btree (order_id);


--
-- Name: ix_shop_earnings_order_product_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_shop_earnings_order_product_id ON public.shop_earnings USING btree (order_product_id);


--
-- Name: ix_shop_earnings_shop_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_shop_earnings_shop_id ON public.shop_earnings USING btree (shop_id);


--
-- Name: ix_shop_withdraw_requests_shop_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_shop_withdraw_requests_shop_id ON public.shop_withdraw_requests USING btree (shop_id);


--
-- Name: ix_shop_withdraw_requests_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_shop_withdraw_requests_status ON public.shop_withdraw_requests USING btree (status);


--
-- Name: ix_shops_slug; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_shops_slug ON public.shops USING btree (slug);


--
-- Name: ix_user_wallets_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_user_wallets_user_id ON public.user_wallets USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_wallet_transactions_transfer_eligible_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_transactions_transfer_eligible_at ON public.wallet_transactions USING btree (transfer_eligible_at);


--
-- Name: ix_wallet_transactions_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_transactions_user_id ON public.wallet_transactions USING btree (user_id);


--
-- Name: ix_wishlists_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wishlists_user_id ON public.wishlists USING btree (user_id);


--
-- Name: ix_wishlists_variation_option_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wishlists_variation_option_id ON public.wishlists USING btree (variation_option_id);


--
-- Name: address address_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.address
    ADD CONSTRAINT address_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.users(id);


--
-- Name: attribute_product attribute_product_attribute_value_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.attribute_product
    ADD CONSTRAINT attribute_product_attribute_value_id_fkey FOREIGN KEY (attribute_value_id) REFERENCES public.attribute_values(id);


--
-- Name: attribute_product attribute_product_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.attribute_product
    ADD CONSTRAINT attribute_product_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: attribute_values attribute_values_attribute_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.attribute_values
    ADD CONSTRAINT attribute_values_attribute_id_fkey FOREIGN KEY (attribute_id) REFERENCES public.attributes(id);


--
-- Name: banners banners_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.banners
    ADD CONSTRAINT banners_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id);


--
-- Name: carts carts_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.carts
    ADD CONSTRAINT carts_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: carts carts_shop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.carts
    ADD CONSTRAINT carts_shop_id_fkey FOREIGN KEY (shop_id) REFERENCES public.shops(id);


--
-- Name: carts carts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.carts
    ADD CONSTRAINT carts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: categories categories_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.categories(id);


--
-- Name: categories categories_root_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_root_id_fkey FOREIGN KEY (root_id) REFERENCES public.categories(id);


--
-- Name: reviews fk_reviews_order_id; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT fk_reviews_order_id FOREIGN KEY (order_id) REFERENCES public.orders(id);


--
-- Name: reviews fk_reviews_product_id; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT fk_reviews_product_id FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: reviews fk_reviews_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT fk_reviews_shop_id FOREIGN KEY (shop_id) REFERENCES public.shops(id);


--
-- Name: reviews fk_reviews_user_id; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT fk_reviews_user_id FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: reviews fk_reviews_variation_option_id; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT fk_reviews_variation_option_id FOREIGN KEY (variation_option_id) REFERENCES public.variation_options(id);


--
-- Name: wishlists fk_wishlists_product_id; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wishlists
    ADD CONSTRAINT fk_wishlists_product_id FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: wishlists fk_wishlists_user_id; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wishlists
    ADD CONSTRAINT fk_wishlists_user_id FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: wishlists fk_wishlists_variation_option_id; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wishlists
    ADD CONSTRAINT fk_wishlists_variation_option_id FOREIGN KEY (variation_option_id) REFERENCES public.variation_options(id);


--
-- Name: media media_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.media
    ADD CONSTRAINT media_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: order_product order_product_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.order_product
    ADD CONSTRAINT order_product_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id);


--
-- Name: order_product order_product_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.order_product
    ADD CONSTRAINT order_product_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: order_product order_product_shop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.order_product
    ADD CONSTRAINT order_product_shop_id_fkey FOREIGN KEY (shop_id) REFERENCES public.shops(id);


--
-- Name: order_product order_product_variation_option_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.order_product
    ADD CONSTRAINT order_product_variation_option_id_fkey FOREIGN KEY (variation_option_id) REFERENCES public.variation_options(id);


--
-- Name: orders orders_coupon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES public.coupons(id);


--
-- Name: orders orders_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.users(id);


--
-- Name: orders orders_fullfillment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_fullfillment_id_fkey FOREIGN KEY (fullfillment_id) REFERENCES public.users(id);


--
-- Name: orders_status orders_status_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders_status
    ADD CONSTRAINT orders_status_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id);


--
-- Name: product_import_history product_import_history_imported_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_import_history
    ADD CONSTRAINT product_import_history_imported_by_fkey FOREIGN KEY (imported_by) REFERENCES public.users(id);


--
-- Name: product_import_history product_import_history_shop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_import_history
    ADD CONSTRAINT product_import_history_shop_id_fkey FOREIGN KEY (shop_id) REFERENCES public.shops(id);


--
-- Name: product_purchase product_purchase_added_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_purchase
    ADD CONSTRAINT product_purchase_added_by_fkey FOREIGN KEY (added_by) REFERENCES public.users(id);


--
-- Name: product_purchase product_purchase_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_purchase
    ADD CONSTRAINT product_purchase_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: product_purchase product_purchase_shop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_purchase
    ADD CONSTRAINT product_purchase_shop_id_fkey FOREIGN KEY (shop_id) REFERENCES public.shops(id);


--
-- Name: product_purchase product_purchase_variation_option_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_purchase
    ADD CONSTRAINT product_purchase_variation_option_id_fkey FOREIGN KEY (variation_option_id) REFERENCES public.variation_options(id);


--
-- Name: product_purchase_variation_options product_purchase_variation_options_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_purchase_variation_options
    ADD CONSTRAINT product_purchase_variation_options_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: product_purchase_variation_options product_purchase_variation_options_product_purchase_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_purchase_variation_options
    ADD CONSTRAINT product_purchase_variation_options_product_purchase_id_fkey FOREIGN KEY (product_purchase_id) REFERENCES public.product_purchase(id);


--
-- Name: product_purchase_variation_options product_purchase_variation_options_variation_options_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_purchase_variation_options
    ADD CONSTRAINT product_purchase_variation_options_variation_options_id_fkey FOREIGN KEY (variation_options_id) REFERENCES public.variation_options(id);


--
-- Name: products products_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id);


--
-- Name: products products_manufacturer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_manufacturer_id_fkey FOREIGN KEY (manufacturer_id) REFERENCES public.manufacturers(id);


--
-- Name: products products_shop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_shop_id_fkey FOREIGN KEY (shop_id) REFERENCES public.shops(id);


--
-- Name: return_items return_items_order_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.return_items
    ADD CONSTRAINT return_items_order_item_id_fkey FOREIGN KEY (order_item_id) REFERENCES public.order_product(id);


--
-- Name: return_items return_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.return_items
    ADD CONSTRAINT return_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: return_items return_items_return_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.return_items
    ADD CONSTRAINT return_items_return_request_id_fkey FOREIGN KEY (return_request_id) REFERENCES public.return_requests(id);


--
-- Name: return_items return_items_variation_option_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.return_items
    ADD CONSTRAINT return_items_variation_option_id_fkey FOREIGN KEY (variation_option_id) REFERENCES public.variation_options(id);


--
-- Name: return_requests return_requests_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.return_requests
    ADD CONSTRAINT return_requests_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id);


--
-- Name: return_requests return_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.return_requests
    ADD CONSTRAINT return_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: return_requests return_requests_wallet_credit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.return_requests
    ADD CONSTRAINT return_requests_wallet_credit_id_fkey FOREIGN KEY (wallet_credit_id) REFERENCES public.wallet_transactions(id);


--
-- Name: roles roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: shop_earnings shop_earnings_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shop_earnings
    ADD CONSTRAINT shop_earnings_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id);


--
-- Name: shop_earnings shop_earnings_order_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shop_earnings
    ADD CONSTRAINT shop_earnings_order_product_id_fkey FOREIGN KEY (order_product_id) REFERENCES public.order_product(id);


--
-- Name: shop_earnings shop_earnings_shop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shop_earnings
    ADD CONSTRAINT shop_earnings_shop_id_fkey FOREIGN KEY (shop_id) REFERENCES public.shops(id);


--
-- Name: shop_withdraw_requests shop_withdraw_requests_cash_handled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shop_withdraw_requests
    ADD CONSTRAINT shop_withdraw_requests_cash_handled_by_fkey FOREIGN KEY (cash_handled_by) REFERENCES public.users(id);


--
-- Name: shop_withdraw_requests shop_withdraw_requests_processed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shop_withdraw_requests
    ADD CONSTRAINT shop_withdraw_requests_processed_by_fkey FOREIGN KEY (processed_by) REFERENCES public.users(id);


--
-- Name: shop_withdraw_requests shop_withdraw_requests_shop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shop_withdraw_requests
    ADD CONSTRAINT shop_withdraw_requests_shop_id_fkey FOREIGN KEY (shop_id) REFERENCES public.shops(id);


--
-- Name: shops shops_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.shops
    ADD CONSTRAINT shops_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: user_roles user_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: user_roles user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_shop user_shop_shop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_shop
    ADD CONSTRAINT user_shop_shop_id_fkey FOREIGN KEY (shop_id) REFERENCES public.shops(id);


--
-- Name: user_shop user_shop_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_shop
    ADD CONSTRAINT user_shop_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_wallets user_wallets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_wallets
    ADD CONSTRAINT user_wallets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: variation_options variation_options_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.variation_options
    ADD CONSTRAINT variation_options_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: wallet_transactions wallet_transactions_return_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallet_transactions
    ADD CONSTRAINT wallet_transactions_return_request_id_fkey FOREIGN KEY (return_request_id) REFERENCES public.return_requests(id);


--
-- Name: wallet_transactions wallet_transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallet_transactions
    ADD CONSTRAINT wallet_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO neon_superuser WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON TABLES TO neon_superuser WITH GRANT OPTION;


--
-- PostgreSQL database dump complete
--

\unrestrict 5rVlTucyhOme78N2DgmmL4EfpKZJo566L4cbmWAsN5B9BQplZAaZqOhVgIaAdiz

