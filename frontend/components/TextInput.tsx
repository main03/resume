interface Props {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  maxLength: number;
}

export default function TextInput({ id, label, placeholder, value, onChange, maxLength }: Props) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <textarea
        id={id}
        placeholder={placeholder}
        value={value}
        maxLength={maxLength}
        onChange={(e) => onChange(e.target.value)}
      />
      <span className="char-count muted">
        {value.length.toLocaleString()} / {maxLength.toLocaleString()}
      </span>
    </div>
  );
}
