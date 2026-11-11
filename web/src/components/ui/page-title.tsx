// The site's hero treatment: the last word of the title is set in the link blue.
export function PageTitle({ children }: { children: string }) {
  const index = children.lastIndexOf(" ") + 1;
  return (
    <h1 className="text-3xl sm:text-4xl">
      {children.slice(0, index)}
      <span className="text-link">{children.slice(index)}</span>
    </h1>
  );
}
