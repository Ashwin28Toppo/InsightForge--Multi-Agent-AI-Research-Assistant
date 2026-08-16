"use client";

import React from "react";

type InlineToken =
  | { type: "text"; value: string }
  | { type: "bold"; value: string }
  | { type: "italic"; value: string }
  | { type: "code"; value: string }
  | { type: "citation"; value: number };

/**
 * Parse a constrained markdown subset into inline tokens:
 * **bold**, *italic*, `code`, and inline citations [1] / [2].
 */
function parseInline(text: string): InlineToken[] {
  const tokens: InlineToken[] = [];
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[(\d+)\])/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push({ type: "text", value: text.slice(lastIndex, match.index) });
    }
    const token = match[0];
    if (token.startsWith("**")) {
      tokens.push({ type: "bold", value: token.slice(2, -2) });
    } else if (token.startsWith("`")) {
      tokens.push({ type: "code", value: token.slice(1, -1) });
    } else if (token.startsWith("[")) {
      tokens.push({
        type: "citation",
        value: parseInt(token.slice(1, -1), 10),
      });
    } else {
      tokens.push({ type: "italic", value: token.slice(1, -1) });
    }
    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) {
    tokens.push({ type: "text", value: text.slice(lastIndex) });
  }
  return tokens;
}

interface MarkdownRendererProps {
  markdown: string;
  /** Called when an inline citation [n] is clicked. */
  onCitationRef?: (index: number) => void;
}

function Inline({
  text,
  onCitationRef,
}: {
  text: string;
  onCitationRef?: (index: number) => void;
}) {
  const tokens = parseInline(text);
  return (
    <>
      {tokens.map((token, i) => {
        switch (token.type) {
          case "bold":
            return (
              <strong key={i} className="font-semibold text-foreground">
                <Inline text={token.value} onCitationRef={onCitationRef} />
              </strong>
            );
          case "italic":
            return (
              <em key={i} className="italic text-foreground/90">
                <Inline text={token.value} onCitationRef={onCitationRef} />
              </em>
            );
          case "code":
            return (
              <code
                key={i}
                className="px-1 py-0.5 rounded bg-muted border border-border font-mono text-[0.85em] text-primary"
              >
                {token.value}
              </code>
            );
          case "citation":
            return (
              <button
                key={i}
                type="button"
                onClick={() => onCitationRef?.(token.value)}
                className="inline-flex items-center justify-center h-4 min-w-4 px-0.5 mx-0.5 rounded bg-primary/10 border border-primary/25 text-[10px] font-mono font-bold text-primary align-baseline hover:bg-primary/20 hover:underline cursor-pointer transition-colors"
                aria-label={`Citation ${token.value}`}
              >
                {token.value}
              </button>
            );
          default:
            return <React.Fragment key={i}>{token.value}</React.Fragment>;
        }
      })}
    </>
  );
}

export default function MarkdownRenderer({
  markdown,
  onCitationRef,
}: MarkdownRendererProps) {
  const lines = markdown.split(/\r?\n/);
  const blocks: React.ReactNode[] = [];
  let key = 0;

  const pushParagraph = (buffer: string[]) => {
    if (buffer.length === 0) return;
    blocks.push(
      <p key={key++} className="text-sm md:text-[15px] text-foreground/90 leading-7">
        <Inline text={buffer.join(" ")} onCitationRef={onCitationRef} />
      </p>
    );
    buffer.length = 0;
  };

  const buffer: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Headings
    const heading = /^(#{1,3})\s+(.*)$/.exec(line);
    if (heading) {
      pushParagraph(buffer);
      const level = heading[1].length;
      const content = heading[2];
      if (level === 1) {
        blocks.push(
          <h1 key={key++} className="text-2xl md:text-3xl font-bold font-syne tracking-tight text-foreground mt-2 mb-4">
            <Inline text={content} onCitationRef={onCitationRef} />
          </h1>
        );
      } else if (level === 2) {
        blocks.push(
          <h2 key={key++} className="text-lg md:text-xl font-bold font-syne tracking-tight text-foreground mt-8 mb-3 pb-2 border-b border-border">
            <Inline text={content} onCitationRef={onCitationRef} />
          </h2>
        );
      } else {
        blocks.push(
          <h3 key={key++} className="text-base font-semibold text-foreground mt-6 mb-2">
            <Inline text={content} onCitationRef={onCitationRef} />
          </h3>
        );
      }
      continue;
    }

    // Horizontal rule
    if (/^-{3,}$/.test(line.trim())) {
      pushParagraph(buffer);
      blocks.push(<hr key={key++} className="my-8 border-border" />);
      continue;
    }

    // Blockquote (group consecutive)
    if (line.startsWith("> ")) {
      pushParagraph(buffer);
      const quote: string[] = [];
      while (i < lines.length && lines[i].startsWith("> ")) {
        quote.push(lines[i].slice(2));
        i++;
      }
      i--;
      blocks.push(
        <blockquote
          key={key++}
          className="border-l-2 border-primary/40 pl-4 my-4 text-sm text-muted-foreground italic"
        >
          <Inline text={quote.join(" ")} onCitationRef={onCitationRef} />
        </blockquote>
      );
      continue;
    }

    // Unordered list (group consecutive)
    if (/^[-*]\s+/.test(line)) {
      pushParagraph(buffer);
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s+/, ""));
        i++;
      }
      i--;
      blocks.push(
        <ul key={key++} className="space-y-1.5 my-4 list-none">
          {items.map((item, idx) => (
            <li key={idx} className="flex gap-2.5 text-sm text-foreground/90 leading-6">
              <span className="text-primary font-mono text-xs mt-1 select-none" aria-hidden="true">
                ▸
              </span>
              <span>
                <Inline text={item} onCitationRef={onCitationRef} />
              </span>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Ordered list (group consecutive)
    if (/^\d+\.\s+/.test(line)) {
      pushParagraph(buffer);
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s+/, ""));
        i++;
      }
      i--;
      blocks.push(
        <ol key={key++} className="space-y-1.5 my-4 list-none">
          {items.map((item, idx) => (
            <li key={idx} className="flex gap-2.5 text-sm text-foreground/90 leading-6">
              <span className="text-primary font-mono text-xs mt-1 shrink-0 select-none" aria-hidden="true">
                {idx + 1}.
              </span>
              <span>
                <Inline text={item} onCitationRef={onCitationRef} />
              </span>
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // Blank line — flush paragraph
    if (line.trim() === "") {
      pushParagraph(buffer);
      continue;
    }

    // Regular line → accumulate into paragraph
    buffer.push(line.trim());
  }

  pushParagraph(buffer);

  return (
    <div className="space-y-4 max-w-none" role="article">
      {blocks}
    </div>
  );
}
