export interface GbFeature {
  type: string;
  label: string;
  start: number;
  end: number;
  strand: 1 | -1;
  color: string;
}

export interface GbRecord {
  name: string;
  length: number;
  features: GbFeature[];
}

const FEATURE_COLORS: Record<string, string> = {
  cds: "#22c55e",
  promoter: "#f59e0b",
  terminator: "#ef4444",
  rep_origin: "#3b82f6",
  primer_bind: "#8b5cf6",
  misc_feature: "#64748b",
  gene: "#14b8a6",
  source: "#94a3b8",
};

function featureColor(type: string) {
  return FEATURE_COLORS[type.toLowerCase()] ?? "#94a3b8";
}

function parseLocation(location: string) {
  const strand: 1 | -1 = location.includes("complement") ? -1 : 1;
  const numbers = Array.from(location.matchAll(/\d+/g), (match) => Number(match[0]));
  if (numbers.length === 0) {
    return null;
  }

  return {
    start: Math.min(...numbers),
    end: Math.max(...numbers),
    strand,
  };
}

function locusLength(text: string) {
  const locusMatch = text.match(/^LOCUS\s+\S+\s+(\d+)\s+bp/im);
  if (locusMatch) {
    return Number(locusMatch[1]);
  }

  const originMatch = text.match(/^ORIGIN([\s\S]+?)^\/\//m);
  if (!originMatch) {
    return 0;
  }

  return Array.from(originMatch[1]).filter((char) => /[A-Za-z]/.test(char)).length;
}

export function parseGenbank(text: string): GbRecord {
  const lines = text.split(/\r?\n/);
  const locus = lines.find((line) => line.startsWith("LOCUS")) ?? "";
  const name = locus.trim().split(/\s+/)[1] ?? "Untitled";
  const features: GbFeature[] = [];

  let inFeatures = false;
  let current:
    | {
        type: string;
        location: string;
        qualifiers: Record<string, string>;
      }
    | null = null;
  let activeQualifier: string | null = null;

  const flushCurrent = () => {
    if (!current) {
      return;
    }

    const parsed = parseLocation(current.location);
    if (!parsed) {
      current = null;
      activeQualifier = null;
      return;
    }

    const label =
      current.qualifiers.label ??
      current.qualifiers.gene ??
      current.qualifiers.locus_tag ??
      current.qualifiers.note ??
      current.type;

    features.push({
      type: current.type,
      label,
      start: parsed.start,
      end: parsed.end,
      strand: parsed.strand,
      color: featureColor(current.type),
    });

    current = null;
    activeQualifier = null;
  };

  for (const line of lines) {
    if (line.startsWith("FEATURES")) {
      inFeatures = true;
      continue;
    }
    if (line.startsWith("ORIGIN")) {
      flushCurrent();
      break;
    }
    if (!inFeatures) {
      continue;
    }

    const featureMatch = line.match(/^\s{5}(\S+)\s+(.+)$/);
    if (featureMatch) {
      flushCurrent();
      current = {
        type: featureMatch[1],
        location: featureMatch[2].trim(),
        qualifiers: {},
      };
      continue;
    }

    const qualifierMatch = line.match(/^\s+\/([\w-]+)=?(.*)$/);
    if (qualifierMatch && current) {
      activeQualifier = qualifierMatch[1];
      current.qualifiers[activeQualifier] = qualifierMatch[2].trim().replace(/^"|"$/g, "");
      continue;
    }

    if (current && activeQualifier && line.startsWith("                     ")) {
      current.qualifiers[activeQualifier] += line.trim().replace(/^"|"$/g, "");
    }
  }

  return {
    name,
    length: locusLength(text),
    features,
  };
}
