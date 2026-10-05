/* Throughline engine — DOM-free so it can be unit-tested in Node.
   Data generation mirrors src/throughline/data_gen.py exactly (same seeded PRNG),
   so the browser prototype and the Python/DuckDB service return identical numbers. */
const Engine = (() => {
  const DAY = 86400000;
  const d = s => Math.round(Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)) / DAY);
  const iso = n => new Date(n * DAY).toISOString().slice(0, 10);
  const AS_OF = d('2026-09-30'), YEAR_START = d('2026-01-01');
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const fmtDate = n => { const x = new Date(n * DAY); return x.getUTCDate() + ' ' + MONTHS[x.getUTCMonth()] + ' ' + x.getUTCFullYear(); };

  function mulberry32(seed) {
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  const R = mulberry32(20261005);
  const ri = (a, b) => a + Math.floor(R() * (b - a + 1));
  const pick = a => a[Math.floor(R() * a.length)];

  // ---------- Master data (the ontology's entity instances) ----------
  const SUPPLIERS = [
    { id: 'S01', name: 'Kaveri Castings', country: 'IN', rel: 0.93, tier: 1, erp: '0000100023', portal: 'KAV-IN-01', tms: 'KAVERI CASTINGS PVT LTD' },
    { id: 'S02', name: 'Nordhavn Electronics', country: 'DK', rel: 0.95, tier: 1, erp: '0000100031', portal: 'NOR-DK-02', tms: 'NORDHAVN ELEC A/S' },
    { id: 'S03', name: 'Shenzhen Lumen', country: 'CN', rel: 0.82, tier: 1, erp: '0000100044', portal: 'SZL-CN-07', tms: 'SHENZHEN LUMEN TECH CO' },
    { id: 'S04', name: 'Saltillo Polymers', country: 'MX', rel: 0.88, tier: 2, erp: '0000100052', portal: 'SAL-MX-03', tms: 'SALTILLO POLIMEROS SA' },
    { id: 'S05', name: 'Osaka Precision', country: 'JP', rel: 0.97, tier: 1, erp: '0000100067', portal: 'OSK-JP-01', tms: 'OSAKA PRECISION KK' },
    { id: 'S06', name: 'Ruhr Steelworks', country: 'DE', rel: 0.90, tier: 2, erp: '0000100071', portal: 'RUH-DE-04', tms: 'RUHR STAHLWERK GMBH' },
    { id: 'S07', name: 'Penang Microsystems', country: 'MY', rel: 0.85, tier: 1, erp: '0000100088', portal: 'PEN-MY-02', tms: 'PENANG MICROSYSTEMS SDN BHD' },
    { id: 'S08', name: 'Ohio Fasteners', country: 'US', rel: 0.91, tier: 2, erp: '0000100090', portal: 'OHF-US-05', tms: 'OHIO FASTENERS INC' }
  ];
  const PARTS = [
    ['P101', 'Motor controller board', 'Electronics', 'S02', 42], ['P102', 'Li-ion cell pack', 'Electronics', 'S03', 65],
    ['P103', 'Display module', 'Electronics', 'S07', 38], ['P104', 'Sensor array', 'Electronics', 'S05', 27],
    ['P105', 'Battery management IC', 'Electronics', 'S07', 9.5], ['P106', 'Power switch', 'Electronics', 'S03', 3.2],
    ['P107', 'Aluminium housing', 'Mechanical', 'S01', 18], ['P108', 'Gear assembly', 'Mechanical', 'S05', 24],
    ['P109', 'Steel bracket', 'Mechanical', 'S06', 4.1], ['P110', 'Fastener kit', 'Mechanical', 'S08', 1.8],
    ['P111', 'Wiring harness', 'Mechanical', 'S04', 6.5], ['P112', 'Thermal pad', 'Raw material', 'S04', 0.9],
    ['P113', 'Polymer resin', 'Raw material', 'S04', 2.4], ['P114', 'Cold-rolled steel coil', 'Raw material', 'S06', 1.1],
    ['P115', 'Corrugated carton', 'Packaging', 'S01', 0.6], ['P116', 'Foam insert', 'Packaging', 'S08', 0.4]
  ].map(([id, name, category, supplier, cost]) => ({ id, name, category, supplier, cost }));
  const PLANTS = [
    { id: 'PL1', name: 'Chennai', country: 'IN', region: 'APAC' }, { id: 'PL2', name: 'Pune', country: 'IN', region: 'APAC' },
    { id: 'PL3', name: 'Monterrey', country: 'MX', region: 'Americas' }, { id: 'PL4', name: 'Rotterdam', country: 'NL', region: 'EMEA' }
  ];
  const CUSTOMERS = [
    ['C01', 'Arcadia Retail', 'Retail', 'Americas'], ['C02', 'Bharat Mobility', 'OEM', 'APAC'], ['C03', 'Lindqvist Distribution', 'Distributor', 'EMEA'],
    ['C04', 'Sakura Home', 'Retail', 'APAC'], ['C05', 'Volta Motors', 'OEM', 'EMEA'], ['C06', 'Pacific Wholesale', 'Distributor', 'APAC'],
    ['C07', 'Meridian Appliances', 'OEM', 'Americas'], ['C08', 'Hanse Handel', 'Distributor', 'EMEA'], ['C09', 'Deccan Electricals', 'Retail', 'APAC'],
    ['C10', 'Rio Grande Supply', 'Distributor', 'Americas']
  ].map(([id, name, segment, region]) => ({ id, name, segment, region }));
  const CARRIERS = [
    { id: 'CR1', name: 'BlueDart', mode: 'Road', region: 'APAC', perf: 0.90 }, { id: 'CR2', name: 'Delhivery', mode: 'Road', region: 'APAC', perf: 0.84 },
    { id: 'CR3', name: 'DB Schenker', mode: 'Road', region: 'EMEA', perf: 0.92 }, { id: 'CR4', name: 'J.B. Hunt', mode: 'Road', region: 'Americas', perf: 0.89 },
    { id: 'CR5', name: 'Maersk', mode: 'Ocean', region: null, perf: 0.78 }, { id: 'CR6', name: 'DHL Express', mode: 'Air', region: null, perf: 0.95 },
    { id: 'CR7', name: 'FedEx', mode: 'Air', region: null, perf: 0.91 }
  ];
  const SUP = Object.fromEntries(SUPPLIERS.map(s => [s.id, s]));
  const CAR = Object.fromEntries(CARRIERS.map(c => [c.id, c]));
  const LEAD = { Road: 7, Air: 6, Ocean: 32 };
  const RATE = { Road: 0.12, Ocean: 0.08, Air: 0.55 };

  // ---------- Transactions (orders from ERP/OMS, shipments from TMS, telemetry from IoT) ----------
  const FACT = [];
  for (let i = 0; i < 760; i++) {
    const od = YEAR_START + ri(0, 266);
    const cust = pick(CUSTOMERS);
    const local = PLANTS.filter(p => p.region === cust.region);
    const plant = R() < 0.65 ? pick(local) : pick(PLANTS);
    const part = pick(PARTS);
    const sup = SUP[part.supplier];
    const cross = plant.region !== cust.region;
    let carrier;
    if (!cross) carrier = pick(CARRIERS.filter(c => c.mode === 'Road' && c.region === plant.region));
    else carrier = R() < 0.62 ? CAR.CR5 : pick([CAR.CR6, CAR.CR7]);
    const mode = carrier.mode;
    const promised = od + LEAD[mode];
    const proc = ri(1, 2);
    const supDelay = R() > sup.rel ? ri(2, 7) : 0;
    const ship = od + proc + supDelay;
    const transit = mode === 'Road' ? ri(3, 4) : mode === 'Air' ? ri(2, 3) : ri(24, 28);
    const carDelay = R() > carrier.perf ? ri(1, 6) : 0;
    const deliv = ship + transit + carDelay;
    const qo = ri(5, 60) * 10;
    let qs = qo;
    const partial = R() > 0.86;
    if (partial || (supDelay > 0 && R() < 0.35)) qs = Math.round(qo * (0.55 + R() * 0.4));
    const shipped = ship <= AS_OF;
    if (!shipped) qs = 0;
    const delivered = shipped && deliv <= AS_OF;
    const freight = shipped ? Math.round(qs * RATE[mode] * (0.5 + part.cost / 40) * 100) / 100 : 0;
    const duty = (shipped && sup.country !== plant.country) ? Math.round(qs * part.cost * 0.06 * 100) / 100 : 0;
    const e = R();
    const excursion = delivered && ((part.category === 'Electronics' && mode === 'Ocean' && e < 0.18) || e < 0.02);
    FACT.push({
      order_id: 'SO-' + String(240001 + i), od, promised, ship: shipped ? ship : null, deliv: delivered ? deliv : null,
      shipped, delivered, qo, qs, freight, duty, excursion, part, supplier: sup, plant, customer: cust, carrier, mode
    });
  }
  const INVENTORY = [];
  for (const p of PLANTS) for (const pt of PARTS) {
    if (R() < 0.8) INVENTORY.push({ plant: p, part: pt, supplier: SUP[pt.supplier], on_hand: Math.round((100 + R() * 2900) * (12 / (pt.cost + 12))) + 20 });
  }

  // ---------- Ontology ----------
  const CHAIN = ['Supplier', 'Part', 'Plant', 'Shipment', 'Order', 'Customer'];
  const RELS = [
    { from: 'Supplier', to: 'Part', label: 'supplies', card: '1 : N' },
    { from: 'Part', to: 'Plant', label: 'stocked at', card: 'N : M via Inventory' },
    { from: 'Plant', to: 'Shipment', label: 'dispatches', card: '1 : N' },
    { from: 'Shipment', to: 'Order', label: 'fulfils', card: 'N : 1' },
    { from: 'Order', to: 'Customer', label: 'placed by', card: 'N : 1' }
  ];
  const ENTITIES = {
    Supplier: { key: 'supplier_id', desc: 'A company that supplies parts.', attrs: ['supplier_name', 'country', 'tier'], hierarchy: 'Supplier → Country',
      sources: [['ERP vendor master', 'LIFNR'], ['Supplier portal', 'vendor_code'], ['TMS', 'shipper_name (free text)']] },
    Part: { key: 'part_id', desc: 'A purchased component or material.', attrs: ['part_name', 'category', 'unit_cost'], hierarchy: 'Part → Category',
      sources: [['ERP material master', 'MATNR'], ['Supplier portal', 'supplier_sku']] },
    Plant: { key: 'plant_id', desc: 'A site that stocks parts and dispatches shipments.', attrs: ['plant_name', 'country', 'region'], hierarchy: 'Plant → Region',
      sources: [['ERP', 'WERKS'], ['WMS', 'site_code'], ['TMS', 'origin_location']] },
    Shipment: { key: 'shipment_id', desc: 'A physical movement that fulfils an order line.', attrs: ['ship_date', 'delivered_date', 'qty_shipped', 'carrier', 'mode', 'freight_cost', 'duty_cost', 'iot_excursion'], hierarchy: 'Carrier → Mode',
      sources: [['TMS', 'load_id'], ['IoT telemetry', 'tracker_id → load_id'], ['ERP', 'delivery document (VBELN)']] },
    Order: { key: 'order_id', desc: 'A customer order line for a part from a plant.', attrs: ['order_date', 'promised_date', 'qty_ordered'], hierarchy: 'Day → Month → Quarter',
      sources: [['ERP / OMS', 'VBAP (order line)'], ['Planning spreadsheet', 'order_ref']] },
    Customer: { key: 'customer_id', desc: 'The account that places orders.', attrs: ['customer_name', 'segment', 'region'], hierarchy: 'Customer → Segment, Region',
      sources: [['CRM', 'account_id'], ['ERP', 'KUNNR']] }
  };

  // ---------- Dimensions (ontology attributes exposed to the semantic layer) ----------
  const DIMS = {
    supplier: { label: 'Supplier', entity: 'Supplier', key: r => r.supplier.name, col: 'sup.supplier_name' },
    part: { label: 'Part', entity: 'Part', key: r => r.part.name, col: 'pt.part_name' },
    category: { label: 'Part category', entity: 'Part', key: r => r.part.category, col: 'pt.category' },
    plant: { label: 'Plant', entity: 'Plant', key: r => r.plant.name, col: 'pl.plant_name' },
    region: { label: 'Plant region', entity: 'Plant', key: r => r.plant.region, col: 'pl.region' },
    customer: { label: 'Customer', entity: 'Customer', key: r => r.customer.name, col: 'c.customer_name' },
    segment: { label: 'Customer segment', entity: 'Customer', key: r => r.customer.segment, col: 'c.segment' },
    carrier: { label: 'Carrier', entity: 'Shipment', key: r => r.shipped ? r.carrier.name : '(not yet shipped)', col: "COALESCE(s.carrier_name, '(not yet shipped)')" },
    mode: { label: 'Transport mode', entity: 'Shipment', key: r => r.shipped ? r.mode : '(not yet shipped)', col: "COALESCE(s.transport_mode, '(not yet shipped)')" },
    month: { label: 'Month', entity: 'Order', key: r => iso(r.od).slice(0, 7), col: "STRFTIME(o.order_date, '%Y-%m')" },
    quarter: { label: 'Quarter', entity: 'Order', key: r => '2026-Q' + (Math.floor(new Date(r.od * DAY).getUTCMonth() / 3) + 1), col: "STRFTIME(o.order_date, '%Y') || '-Q' || QUARTER(o.order_date)" }
  };
  const ALL_DIMS = Object.keys(DIMS);
  const INV_DIMS = ['supplier', 'part', 'category', 'plant', 'region'];

  // ---------- Certified metrics (the governed semantic layer) ----------
  const sum = (a, f) => a.reduce((s, r) => s + f(r), 0);
  const METRICS = {
    otd: { label: 'On-time delivery', unit: '%', better: 'higher', view: 'sc_fulfilment', owner: 'Head of Logistics Excellence', steward: 'Logistics', version: '2.1', certified: '2026-07-14',
      definition: 'Share of delivered order lines whose delivered date is on or before the promised date. In-transit lines are excluded until delivered.',
      grain: 'Order line', timeAnchor: 'Order date', entities: ['Shipment', 'Order'], dims: ALL_DIMS,
      synonyms: [['on-time delivery', 'all'], ['on time delivery', 'all'], ['otd', 'all'], ['on-time', 'all'], ['on time', 'all'], ['service level', 'planning'], ['supplier punctuality', 'procurement'], ['punctuality', 'procurement'], ['delivery performance', 'logistics']],
      sql: '100.0 * SUM(CASE WHEN s.delivered_date <= o.promised_date THEN 1 ELSE 0 END) / NULLIF(COUNT(s.delivered_date), 0)',
      calc: rows => { const del = rows.filter(r => r.delivered); return { value: del.length ? 100 * del.filter(r => r.deliv <= r.promised).length / del.length : null, n: del.length, nLabel: 'delivered lines' }; } },
    fill_rate: { label: 'Fill rate', unit: '%', better: 'higher', view: 'sc_fulfilment', owner: 'Head of Demand & Supply Planning', steward: 'Planning', version: '1.4', certified: '2026-06-30',
      definition: 'Units shipped divided by units ordered, for order lines whose promised date has passed. Unshipped units on overdue lines count as unfilled.',
      grain: 'Order line', timeAnchor: 'Order date', entities: ['Shipment', 'Order'], dims: ALL_DIMS, where: 'o.promised_date <= DATE \'2026-09-30\'',
      synonyms: [['fill rate', 'all'], ['fill-rate', 'all'], ['unit fill', 'planning'], ['fulfilment rate', 'all'], ['fulfillment rate', 'all']],
      sql: '100.0 * SUM(COALESCE(s.qty_shipped, 0)) / NULLIF(SUM(o.qty_ordered), 0)',
      calc: rows => { const due = rows.filter(r => r.promised <= AS_OF); const qo = sum(due, r => r.qo); return { value: qo ? 100 * sum(due, r => r.qs) / qo : null, n: due.length, nLabel: 'due lines' }; } },
    landed_cost: { label: 'Landed cost per unit', unit: '$', better: 'lower', view: 'sc_fulfilment', owner: 'Head of Strategic Sourcing', steward: 'Procurement', version: '3.0', certified: '2026-08-02',
      definition: 'Purchase price plus freight plus import duty, divided by units shipped.',
      grain: 'Shipment', timeAnchor: 'Order date', entities: ['Part', 'Shipment', 'Order'], dims: ALL_DIMS, where: 's.qty_shipped > 0',
      synonyms: [['landed cost', 'all'], ['total landed cost', 'procurement'], ['unit landed cost', 'procurement'], ['all-in cost', 'procurement'], ['cost per unit', 'all']],
      sql: '(SUM(s.qty_shipped * pt.unit_cost) + SUM(s.freight_cost) + SUM(s.duty_cost)) / NULLIF(SUM(s.qty_shipped), 0)',
      calc: rows => { const sh = rows.filter(r => r.qs > 0); const q = sum(sh, r => r.qs); return { value: q ? (sum(sh, r => r.qs * r.part.cost) + sum(sh, r => r.freight) + sum(sh, r => r.duty)) / q : null, n: sh.length, nLabel: 'shipments' }; } },
    freight_cost: { label: 'Freight cost', unit: '$', better: 'lower', total: true, view: 'sc_fulfilment', owner: 'Head of Logistics Excellence', steward: 'Logistics', version: '1.2', certified: '2026-05-21',
      definition: 'Total carrier freight charged on shipments, excluding duty.',
      grain: 'Shipment', timeAnchor: 'Order date', entities: ['Shipment', 'Order'], dims: ALL_DIMS,
      synonyms: [['freight cost', 'all'], ['freight spend', 'logistics'], ['shipping cost', 'all'], ['transport cost', 'logistics'], ['freight', 'all']],
      sql: 'SUM(s.freight_cost)',
      calc: rows => { const sh = rows.filter(r => r.shipped); return { value: sh.length ? sum(sh, r => r.freight) : null, n: sh.length, nLabel: 'shipments' }; } },
    doi: { label: 'Days of inventory', unit: 'days', better: 'neutral', view: 'sc_inventory', owner: 'Head of Demand & Supply Planning', steward: 'Planning', version: '2.0', certified: '2026-07-01',
      definition: 'Inventory value on hand divided by average daily cost of goods shipped over the trailing 90 days. Snapshot as of 30 Sep 2026.',
      grain: 'Plant × Part', timeAnchor: 'Snapshot date', entities: ['Part', 'Plant'], dims: INV_DIMS,
      synonyms: [['days of inventory', 'all'], ['days of supply', 'planning'], ['doi', 'all'], ['inventory cover', 'planning'], ['stock cover', 'planning'], ['days on hand', 'all'], ['inventory days', 'all']],
      sql: 'SUM(i.on_hand * pt.unit_cost) / NULLIF(SUM(cogs.cogs_90d) / 90.0, 0)' },
    lead_time: { label: 'Order-to-delivery lead time', unit: 'days', better: 'lower', view: 'sc_fulfilment', owner: 'Head of Logistics Excellence', steward: 'Logistics', version: '1.1', certified: '2026-05-21',
      definition: 'Average calendar days from order date to delivered date, for delivered lines.',
      grain: 'Order line', timeAnchor: 'Order date', entities: ['Shipment', 'Order'], dims: ALL_DIMS,
      synonyms: [['lead time', 'all'], ['cycle time', 'planning'], ['order to delivery', 'all'], ['order-to-delivery', 'all'], ['transit time', 'logistics']],
      sql: "AVG(DATE_DIFF('day', o.order_date, s.delivered_date))",
      calc: rows => { const del = rows.filter(r => r.delivered); return { value: del.length ? sum(del, r => r.deliv - r.od) / del.length : null, n: del.length, nLabel: 'delivered lines' }; } },
    excursion: { label: 'Condition excursion rate', unit: '%', better: 'lower', view: 'sc_fulfilment', owner: 'Head of Quality', steward: 'Quality', version: '1.0', certified: '2026-08-19',
      definition: 'Share of delivered shipments where IoT trackers recorded a temperature or shock excursion.',
      grain: 'Shipment', timeAnchor: 'Order date', entities: ['Shipment', 'Order'], dims: ALL_DIMS,
      synonyms: [['excursion', 'all'], ['excursions', 'all'], ['temperature', 'logistics'], ['cold chain', 'logistics'], ['condition breach', 'all'], ['iot alert', 'logistics']],
      sql: '100.0 * SUM(CASE WHEN s.iot_excursion THEN 1 ELSE 0 END) / NULLIF(COUNT(s.delivered_date), 0)',
      calc: rows => { const del = rows.filter(r => r.delivered); return { value: del.length ? 100 * del.filter(r => r.excursion).length / del.length : null, n: del.length, nLabel: 'delivered shipments' }; } },
    late_count: { label: 'Late deliveries', unit: 'count', better: 'lower', total: true, view: 'sc_fulfilment', owner: 'Head of Logistics Excellence', steward: 'Logistics', version: '2.1', certified: '2026-07-14',
      definition: 'Number of delivered order lines whose delivered date is after the promised date. Complement of on-time delivery.',
      grain: 'Order line', timeAnchor: 'Order date', entities: ['Shipment', 'Order'], dims: ALL_DIMS,
      synonyms: [['late shipments', 'all'], ['late deliveries', 'all'], ['late orders', 'all'], ['delayed shipments', 'all'], ['late', 'all']],
      sql: 'SUM(CASE WHEN s.delivered_date > o.promised_date THEN 1 ELSE 0 END)',
      calc: rows => { const del = rows.filter(r => r.delivered); return { value: del.filter(r => r.deliv > r.promised).length, n: del.length, nLabel: 'delivered lines' }; } },
    order_lines: { label: 'Order lines', unit: 'count', better: 'neutral', total: true, view: 'sc_fulfilment', owner: 'Head of Demand & Supply Planning', steward: 'Planning', version: '1.0', certified: '2026-04-10',
      definition: 'Count of customer order lines.',
      grain: 'Order line', timeAnchor: 'Order date', entities: ['Order'], dims: ALL_DIMS,
      synonyms: [['order lines', 'all'], ['number of orders', 'all'], ['order count', 'all'], ['orders', 'all'], ['order volume', 'all']],
      sql: 'COUNT(*)',
      calc: rows => ({ value: rows.length, n: rows.length, nLabel: 'order lines' }) }
  };
  const PRIORITY = ['excursion', 'late_count', 'otd', 'fill_rate', 'doi', 'landed_cost', 'freight_cost', 'lead_time', 'order_lines'];
  const NOT_CERTIFIED = {
    otif: 'OTIF is proposed but not yet certified. It would combine on-time delivery and fill rate, which are both certified — ask for either.',
    revenue: 'Revenue lives in the finance domain and is not part of the supply chain semantic layer.',
    sales: 'Sales value lives in the finance domain and is not part of the supply chain semantic layer.',
    margin: 'Margin lives in the finance domain and is not part of the supply chain semantic layer.',
    profit: 'Profit lives in the finance domain and is not part of the supply chain semantic layer.',
    'forecast accuracy': 'Forecast accuracy is on the roadmap but has no certified definition yet.',
    headcount: 'Headcount is an HR metric, outside this semantic layer.'
  };
  const AMBIGUOUS = {
    cost: { prompt: 'Two certified metrics measure cost. Which one do you mean?', options: [['landed_cost', 'landed cost'], ['freight_cost', 'freight cost']] },
    performance: { prompt: '“Performance” could mean timeliness or completeness. Which one?', options: [['otd', 'on-time delivery'], ['fill_rate', 'fill rate']] },
    spend: { prompt: '“Spend” could mean what you pay per unit or what you pay carriers. Which one?', options: [['landed_cost', 'landed cost'], ['freight_cost', 'freight cost']] }
  };

  // ---------- Policies ----------
  const POLICIES = [
    { id: 'POL-01', name: 'Certified metrics only', text: 'Answers are computed only from metrics with a certified definition, owner and version. Unknown or uncertified terms are refused with alternatives, never guessed.' },
    { id: 'POL-02', name: 'Ontology-valid slicing', text: 'A metric can only be sliced by entities connected to it in the ontology. Days of inventory cannot be split by customer or carrier, because inventory is not related to them.' },
    { id: 'POL-03', name: 'Contract price masking', text: 'Supplier unit prices are visible to Procurement only. Other personas see them masked in record views. Aggregated metric values are unaffected.' },
    { id: 'POL-04', name: 'Small-sample flag', text: 'Any group built from fewer than 5 records is flagged as low confidence rather than presented as a firm number.' },
    { id: 'POL-05', name: 'Plan fingerprint and audit', text: 'Every answer records persona, question, resolved plan and a fingerprint of that plan. The persona is not part of the fingerprint, so equal fingerprints prove equal logic.' }
  ];

  // ---------- Vocabulary for filters ----------
  const VALUE_INDEX = [];
  const addVals = (dim, values, aliasFn) => values.forEach(v => (aliasFn ? aliasFn(v) : [v]).forEach(a => VALUE_INDEX.push({ dim, value: v, alias: a.toLowerCase() })));
  addVals('customer', CUSTOMERS.map(c => c.name), v => [v, v.split(' ')[0] === 'Rio' ? 'Rio Grande' : v.split(' ')[0]]);
  addVals('supplier', SUPPLIERS.map(s => s.name), v => [v, v.split(' ')[0]]);
  addVals('part', PARTS.map(p => p.name));
  addVals('plant', PLANTS.map(p => p.name));
  addVals('carrier', CARRIERS.map(c => c.name), v => v === 'DB Schenker' ? [v, 'Schenker'] : v === 'J.B. Hunt' ? [v, 'JB Hunt', 'Hunt'] : v === 'DHL Express' ? [v, 'DHL'] : [v]);
  addVals('category', ['Electronics', 'Mechanical', 'Raw material', 'Packaging'], v => v === 'Raw material' ? [v, 'raw materials'] : [v]);
  addVals('region', ['APAC', 'EMEA', 'Americas']);
  addVals('segment', ['Retail', 'OEM', 'Distributor'], v => v === 'Distributor' ? [v, 'distributors'] : v === 'OEM' ? [v, 'OEMs'] : [v]);
  addVals('mode', ['Road', 'Ocean', 'Air'], v => v === 'Ocean' ? [v, 'sea'] : v === 'Air' ? [v, 'air freight'] : [v, 'truck']);
  VALUE_INDEX.sort((a, b) => b.alias.length - a.alias.length);

  const DIM_WORDS = [
    ['supplier', /^(suppliers?|vendors?)\b/], ['category', /^(part categor(y|ies)|categor(y|ies))\b/], ['part', /^(parts?|components?|skus?|materials?)\b/],
    ['plant', /^(plants?|sites?|factor(y|ies)|facilit(y|ies)|warehouses?)\b/], ['region', /^(regions?)\b/], ['customer', /^(customers?|accounts?|clients?)\b/],
    ['segment', /^(segments?|customer segments?)\b/], ['carrier', /^(carriers?|transporters?|forwarders?)\b/], ['mode', /^(transport modes?|modes?|shipping modes?)\b/],
    ['month', /^(months?|monthly)\b/], ['quarter', /^(quarters?|quarterly)\b/]
  ];
  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const wordRe = w => new RegExp('(^|[^a-z0-9])' + esc(w) + '(?=$|[^a-z0-9])', 'i');
  const MONTH_RE = /\b(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|june?|july?|aug(ust)?|sep(t(ember)?)?|oct(ober)?|nov(ember)?|dec(ember)?)\b/gi;
  const monthIdx = m => ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'].indexOf(m.slice(0, 3).toLowerCase());
  const monthEnd = (y, m) => d(new Date(Date.UTC(y, m + 1, 0)).toISOString().slice(0, 10));
  const monthStart = (y, m) => d(new Date(Date.UTC(y, m, 1)).toISOString().slice(0, 10));

  function parsePeriod(q) {
    const s = q.toLowerCase();
    let m;
    if (/\b(last|previous|prior) quarter\b/.test(s)) return { from: d('2026-07-01'), to: d('2026-09-30'), label: 'Q3 2026' };
    if (/\b(this|current) quarter\b/.test(s)) return { from: d('2026-10-01'), to: d('2026-12-31'), label: 'Q4 2026' };
    if ((m = s.match(/\bq([1-4])\b(?:\s*(?:fy)?\s*'?(20)?(2[0-9]))?/))) {
      const qn = +m[1], y = m[3] ? 2000 + +m[3] : 2026;
      return { from: monthStart(y, (qn - 1) * 3), to: monthEnd(y, qn * 3 - 1), label: 'Q' + qn + ' ' + y };
    }
    if (/\bh1\b|first half/.test(s)) return { from: d('2026-01-01'), to: d('2026-06-30'), label: 'H1 2026' };
    if ((m = s.match(/\blast (\d+) days\b/))) return { from: AS_OF - +m[1] + 1, to: AS_OF, label: 'last ' + m[1] + ' days' };
    if ((m = s.match(/\blast (\d+) months\b/))) { const n = +m[1]; return { from: monthStart(2026, 9 - n), to: AS_OF, label: 'last ' + n + ' months' }; }
    if (/\blast month\b/.test(s)) return { from: d('2026-09-01'), to: d('2026-09-30'), label: 'Sep 2026' };
    const months = [...s.matchAll(MONTH_RE)].map(x => monthIdx(x[1]));
    if (months.length >= 2) { const a = Math.min(months[0], months[1]), b = Math.max(months[0], months[1]); return { from: monthStart(2026, a), to: monthEnd(2026, b), label: MONTHS[a] + '–' + MONTHS[b] + ' 2026' }; }
    if (months.length === 1) return { from: monthStart(2026, months[0]), to: monthEnd(2026, months[0]), label: MONTHS[months[0]] + ' 2026' };
    if (/\b(ytd|year to date|this year|2026)\b/.test(s)) return { from: YEAR_START, to: AS_OF, label: 'year to date 2026' };
    return { from: YEAR_START, to: AS_OF, label: 'year to date 2026', defaulted: true };
  }

  // ---------- Natural language → governed plan ----------
  function parse(question) {
    const raw = question.trim();
    let s = ' ' + raw.toLowerCase().replace(/[?!.,;:]/g, ' ').replace(/\s+/g, ' ') + ' ';
    const notes = [];
    // filters first, blanking matched spans so "Arcadia Retail" doesn't also set segment = Retail
    const filters = [];
    for (const v of VALUE_INDEX) {
      const re = wordRe(v.alias);
      if (re.test(s)) {
        if (!filters.some(f => f.dim === v.dim && f.value === v.value) && !filters.some(f => f.dim === v.dim)) filters.push({ dim: v.dim, value: v.value });
        s = s.replace(re, (m0, pre) => pre + ' '.repeat(m0.length - pre.length));
      }
    }
    // uncertified terms
    for (const [term, msg] of Object.entries(NOT_CERTIFIED)) if (wordRe(term).test(s)) return { status: 'refused', term, message: msg };
    // metric
    let metricId = null, matched = null;
    for (const id of PRIORITY) {
      const syn = METRICS[id].synonyms.map(x => x[0]).sort((a, b) => b.length - a.length).find(w => wordRe(w).test(s));
      if (syn) { metricId = id; matched = syn; break; }
    }
    if (!metricId) {
      for (const [term, a] of Object.entries(AMBIGUOUS)) if (wordRe(term).test(s)) return { status: 'clarify', term, prompt: a.prompt, options: a.options };
      if (/\binventory|stock\b/.test(s)) { metricId = 'doi'; matched = 'inventory'; notes.push('Read “inventory” as days of inventory, the only certified inventory metric.'); }
    }
    if (!metricId) return { status: 'unknown' };
    // dimension
    let dim = null;
    const sNoMetric = s.replace(wordRe(matched), ' ');
    const dm = [...sNoMetric.matchAll(/\b(by|per|for each|for every|across|split by|broken down by|which|what|each|top|best|worst|bottom|highest|lowest)\s+(?:\d+\s+)?([a-z]+(?: [a-z]+)?)/g)];
    for (const mm of dm) { const rest = mm[2].trim(); const hit = DIM_WORDS.find(([, re]) => re.test(rest)); if (hit) { dim = hit[0]; break; } }
    if (!dim && /\b(trend|over time|monthly|month by month|by month)\b/.test(s)) dim = 'month';
    if (!dim && /\bquarterly\b/.test(s)) dim = 'quarter';
    // sort / limit
    let sort = null, limit = null, m;
    if ((m = s.match(/\b(top|best)\s*(\d+)?\b/))) { sort = 'best'; limit = m[2] ? +m[2] : null; }
    if ((m = s.match(/\b(worst|bottom)\s*(\d+)?\b/))) { sort = 'worst'; limit = m[2] ? +m[2] : null; }
    if (!sort && /\b(highest|most)\b/.test(s)) sort = 'desc';
    if (!sort && /\b(lowest|least)\b/.test(s)) sort = 'asc';
    if (/\bwhich\b/.test(s) && dim && !limit && sort) limit = 1;
    const period = METRICS[metricId].timeAnchor === 'Snapshot date' ? { from: YEAR_START, to: AS_OF, label: 'snapshot 30 Sep 2026', snapshot: true } : parsePeriod(raw);
    if (period.defaulted) notes.push('No period given, so this uses year to date (1 Jan – 30 Sep 2026).');
    if (period.snapshot && /\b(q[1-4]|quarter|month|last|ytd|202\d|jan|feb|mar|apr|jun|jul|aug|sep)\b/i.test(raw)) notes.push('Days of inventory is a point-in-time measure; it uses the 30 Sep 2026 snapshot.');
    const plan = { metric: metricId, metricVersion: METRICS[metricId].version, dimension: dim, filters: filters.sort((a, b) => a.dim.localeCompare(b.dim)), period: { from: iso(period.from), to: iso(period.to), label: period.label }, sort, limit };
    return { status: 'ok', plan, matched, notes };
  }

  // ---------- Validation against ontology ----------
  function validate(plan) {
    const M = METRICS[plan.metric];
    const bad = [plan.dimension, ...plan.filters.map(f => f.dim)].filter(x => x && !M.dims.includes(x));
    if (bad.length) {
      const ent = DIMS[bad[0]].entity;
      return { ok: false, policy: 'POL-02', message: M.label + ' is defined at ' + M.grain.toLowerCase() + ' grain and has no path to ' + ent + ' in the ontology, so it cannot be split or filtered by ' + DIMS[bad[0]].label.toLowerCase() + '.', allowed: M.dims.map(x => DIMS[x].label) };
    }
    return { ok: true };
  }

  // ---------- Fingerprint (persona deliberately excluded) ----------
  function fingerprint(plan) {
    const str = JSON.stringify({ m: plan.metric, v: plan.metricVersion, d: plan.dimension, f: plan.filters, p: [plan.period.from, plan.period.to], s: plan.sort, l: plan.limit });
    let h = 0x811c9dc5;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 0x01000193); }
    return 'fp-' + (h >>> 0).toString(16).padStart(8, '0');
  }

  // ---------- Execution ----------
  function execute(plan) {
    const M = METRICS[plan.metric];
    const matchF = r => plan.filters.every(f => DIMS[f.dim].key(r) === f.value);
    let groups;
    if (plan.metric === 'doi') {
      const inv = INVENTORY.filter(matchF);
      const held = new Set(inv.map(r => r.plant.id + '|' + r.part.id)); // mirrors the LEFT JOIN cogs → inventory in SQL
      const cogsRows = FACT.filter(r => r.shipped && r.ship > AS_OF - 90 && r.ship <= AS_OF && held.has(r.plant.id + '|' + r.part.id)).filter(matchF);
      const calc = (invR, cogsR) => { const val = sum(invR, r => r.on_hand * r.part.cost); const cogs = sum(cogsR, r => r.qs * r.part.cost); return { value: cogs > 0 ? val / (cogs / 90) : null, n: invR.length, nLabel: 'stock positions' }; };
      const total = calc(inv, cogsRows);
      groups = plan.dimension ? [...new Set(inv.map(DIMS[plan.dimension].key))].map(k => ({ key: k, ...calc(inv.filter(r => DIMS[plan.dimension].key(r) === k), cogsRows.filter(r => DIMS[plan.dimension].key(r) === k)) })) : [];
      return finish(plan, M, total, groups, inv);
    }
    const from = d(plan.period.from), to = d(plan.period.to);
    const rows = FACT.filter(r => r.od >= from && r.od <= to).filter(matchF);
    const total = M.calc(rows);
    groups = plan.dimension ? [...new Set(rows.map(DIMS[plan.dimension].key))].map(k => ({ key: k, ...M.calc(rows.filter(r => DIMS[plan.dimension].key(r) === k)) })) : [];
    return finish(plan, M, total, groups, rows);
  }
  function finish(plan, M, total, groups, rows) {
    groups.forEach(g => { g.lowConfidence = g.n < 5; });
    const valid = groups.filter(g => g.value !== null);
    const nulls = groups.filter(g => g.value === null);
    const asc = (a, b) => a.value - b.value, desc = (a, b) => b.value - a.value;
    let cmp;
    if (plan.dimension === 'month' || plan.dimension === 'quarter') cmp = (a, b) => a.key.localeCompare(b.key);
    else if (plan.sort === 'asc') cmp = asc; else if (plan.sort === 'desc') cmp = desc;
    else if (plan.sort === 'worst') cmp = M.better === 'lower' ? desc : asc;
    else cmp = M.better === 'lower' ? asc : desc;
    valid.sort(cmp);
    let out = valid.concat(nulls);
    if (plan.limit) out = out.slice(0, plan.limit);
    total.lowConfidence = total.n < 5;
    return { total, groups: out, rows };
  }

  // ---------- SQL compiler (what the warehouse would run) ----------
  function compile(plan) {
    const M = METRICS[plan.metric];
    const dim = plan.dimension ? DIMS[plan.dimension] : null;
    const ents = new Set(M.entities);
    if (dim) ents.add(dim.entity);
    plan.filters.forEach(f => ents.add(DIMS[f.dim].entity));
    const usesSupplier = plan.dimension === 'supplier' || plan.filters.some(f => f.dim === 'supplier');
    if (usesSupplier) ents.add('Part');
    const lit = v => "'" + String(v).replace(/'/g, "''") + "'";
    const where = plan.filters.map(f => DIMS[f.dim].col + ' = ' + lit(f.value));
    if (plan.metric === 'doi') {
      const sel = dim ? dim.col + ' AS ' + plan.dimension + ',\n  ' : '';
      const lines = [
        '-- semantic view: sc_inventory  |  metric: days_of_inventory v' + M.version,
        'WITH cogs AS (',
        '  SELECT o.plant_id, o.part_id, SUM(s.qty_shipped * pt.unit_cost) AS cogs_90d',
        '  FROM fct_shipment s JOIN fct_order_line o ON o.order_id = s.order_id',
        '  JOIN dim_part pt ON pt.part_id = o.part_id',
        "  WHERE s.ship_date > DATE '2026-09-30' - INTERVAL 90 DAY AND s.ship_date <= DATE '2026-09-30'",
        '  GROUP BY 1, 2)',
        'SELECT ' + sel + 'ROUND(' + M.sql + ', 1) AS days_of_inventory',
        'FROM fct_inventory_snapshot i',
        'JOIN dim_part pt ON pt.part_id = i.part_id',
        usesSupplier ? 'JOIN dim_supplier sup ON sup.supplier_id = pt.supplier_id' : null,
        'JOIN dim_plant pl ON pl.plant_id = i.plant_id',
        'LEFT JOIN cogs ON cogs.plant_id = i.plant_id AND cogs.part_id = i.part_id',
        "WHERE i.snapshot_date = DATE '2026-09-30'" + (where.length ? '\n  AND ' + where.join('\n  AND ') : ''),
        dim ? 'GROUP BY 1' : null, dim ? orderBy(plan, M) : null
      ];
      return lines.filter(Boolean).join('\n') + ';';
    }
    const conds = ["o.order_date BETWEEN DATE '" + plan.period.from + "' AND DATE '" + plan.period.to + "'"];
    if (M.where) conds.push(M.where);
    conds.push(...where);
    const joins = [];
    if (ents.has('Shipment')) joins.push('LEFT JOIN fct_shipment s ON s.order_id = o.order_id');
    if (ents.has('Part')) joins.push('JOIN dim_part pt ON pt.part_id = o.part_id');
    if (usesSupplier) joins.push('JOIN dim_supplier sup ON sup.supplier_id = pt.supplier_id');
    if (ents.has('Plant')) joins.push('JOIN dim_plant pl ON pl.plant_id = o.plant_id');
    if (ents.has('Customer')) joins.push('JOIN dim_customer c ON c.customer_id = o.customer_id');
    const alias = plan.metric;
    const lines = [
      '-- semantic view: ' + M.view + '  |  metric: ' + plan.metric + ' v' + M.version,
      'SELECT ' + (dim ? dim.col + ' AS ' + plan.dimension + ',\n       ' : '') + 'ROUND(' + M.sql + ', 2) AS ' + alias,
      'FROM fct_order_line o', ...joins,
      'WHERE ' + conds.join('\n  AND '),
      dim ? 'GROUP BY 1' : null, dim ? orderBy(plan, M) : null,
      plan.limit ? 'LIMIT ' + plan.limit : null
    ];
    return lines.filter(Boolean).join('\n') + ';';
  }
  function orderBy(plan, M) {
    if (plan.dimension === 'month' || plan.dimension === 'quarter') return 'ORDER BY 1';
    const dir = plan.sort === 'asc' ? 'ASC' : plan.sort === 'desc' ? 'DESC' : plan.sort === 'worst' ? (M.better === 'lower' ? 'DESC' : 'ASC') : (M.better === 'lower' ? 'ASC' : 'DESC');
    return 'ORDER BY 2 ' + dir;
  }

  function entitiesTouched(plan) {
    const M = METRICS[plan.metric];
    const set = new Set(M.entities);
    if (plan.dimension) set.add(DIMS[plan.dimension].entity);
    plan.filters.forEach(f => set.add(DIMS[f.dim].entity));
    if (plan.dimension === 'supplier' || plan.filters.some(f => f.dim === 'supplier')) set.add('Supplier');
    const idx = [...set].map(e => CHAIN.indexOf(e)).filter(i => i >= 0);
    const lo = Math.min(...idx), hi = Math.max(...idx);
    return CHAIN.slice(lo, hi + 1);
  }

  // ---------- Raw-source definitions (why the problem exists) ----------
  function rawComparisons(from, to) {
    const F = FACT.filter(r => r.od >= d(from) && r.od <= d(to));
    const due = F.filter(r => r.promised <= AS_OF);
    const del = F.filter(r => r.delivered);
    const sh = F.filter(r => r.qs > 0);
    const shq = sum(sh, r => r.qs);
    const inv = INVENTORY;
    const invVal = sum(inv, r => r.on_hand * r.part.cost), invUnits = sum(inv, r => r.on_hand);
    const win = n => FACT.filter(r => r.shipped && r.ship > AS_OF - n && r.ship <= AS_OF);
    const c30 = sum(win(30), r => r.qs * r.part.cost), u90 = sum(win(90), r => r.qs);
    return {
      otd: { metric: 'otd', canonical: METRICS.otd.calc(F).value, sources: [
        ['ERP', 'Goods issued on or before promised date (ship date, not delivery)', 100 * F.filter(r => r.shipped && r.ship <= r.promised).length / F.filter(r => r.shipped).length],
        ['TMS', 'Delivered within promised date plus a 2-day grace window', 100 * del.filter(r => r.deliv <= r.promised + 2).length / del.length],
        ['Planning sheet', 'Delivered on time ÷ all due lines, in-transit counted as late', 100 * due.filter(r => r.delivered && r.deliv <= r.promised).length / due.length]] },
      fill_rate: { metric: 'fill_rate', canonical: METRICS.fill_rate.calc(F).value, sources: [
        ['ERP', 'Line fill: lines shipped complete ÷ due lines', 100 * due.filter(r => r.qs >= r.qo).length / due.length],
        ['WMS', 'Units picked ÷ units ordered on lines with a shipment; open lines ignored', 100 * sum(F.filter(r => r.shipped), r => r.qs) / sum(F.filter(r => r.shipped), r => r.qo)],
        ['Supplier portal', 'Lines shipped complete ÷ all lines, including lines not yet due', 100 * F.filter(r => r.qs >= r.qo).length / F.length]] },
      landed_cost: { metric: 'landed_cost', canonical: METRICS.landed_cost.calc(F).value, sources: [
        ['ERP', 'Purchase price only', sum(sh, r => r.qs * r.part.cost) / shq],
        ['Finance ledger', 'Purchase price plus duty, freight booked to overhead', (sum(sh, r => r.qs * r.part.cost) + sum(sh, r => r.duty)) / shq],
        ['Procurement sheet', 'Purchase price plus freight, duty omitted', (sum(sh, r => r.qs * r.part.cost) + sum(sh, r => r.freight)) / shq]] },
      doi: { metric: 'doi', canonical: execute({ metric: 'doi', metricVersion: '2.0', dimension: null, filters: [], period: { from: '2026-01-01', to: '2026-09-30' }, sort: null, limit: null }).total.value, sources: [
        ['ERP', 'Inventory value ÷ trailing 30-day daily COGS', invVal / (c30 / 30)],
        ['Planning sheet', 'Units on hand ÷ average daily units shipped (unit-based)', invUnits / (u90 / 90)],
        ['WMS', 'Units on hand ÷ units shipped last 30 days × 30', invUnits / (sum(win(30), r => r.qs) / 30)]] }
    };
  }

  const fmt = (metricId, v) => {
    if (v === null || v === undefined || Number.isNaN(v)) return 'n/a';
    const u = METRICS[metricId].unit;
    if (u === '%') return v.toFixed(1) + '%';
    if (u === '$') return v >= 1000 ? '$' + Math.round(v).toLocaleString('en-US') : '$' + v.toFixed(2);
    if (u === 'days') return v.toFixed(1) + ' days';
    return Math.round(v).toLocaleString('en-US');
  };

  return { parse, validate, execute, compile, fingerprint, entitiesTouched, rawComparisons, fmt, iso, fmtDate, d,
    METRICS, DIMS, ENTITIES, RELS, CHAIN, POLICIES, SUPPLIERS, PARTS, PLANTS, CUSTOMERS, CARRIERS, FACT, INVENTORY, AS_OF, PRIORITY };
})();
if (typeof module !== 'undefined') module.exports = Engine;
