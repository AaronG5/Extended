import React, { useState } from 'react';

function Field({ label, name, type = 'text', value, onChange, placeholder }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-gray-800
                   focus:outline-none focus:ring-2 focus:ring-extended-black focus:border-transparent
                   transition-shadow"
      />
    </div>
  );
}

function ProfilePage() {
  const [form, setForm] = useState({ email: '', name: '', location: '' });
  const [saved, setSaved] = useState(false);

  const handleChange = e => {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }));
    setSaved(false);
  };

  const handleSave = e => {
    e.preventDefault();
    // TODO: replace with API call
    setSaved(true);
  };

  return (
    <div className="max-w-lg mx-auto px-4 py-12">
      <h1 className="text-2xl font-bold text-extended-black mb-2">Profile</h1>
      <p className="text-gray-400 text-sm mb-8">Manage your account details</p>

      <form onSubmit={handleSave} className="space-y-5">
        <Field
          label="Email"
          name="email"
          type="email"
          value={form.email}
          onChange={handleChange}
          placeholder="you@example.com"
        />
        <Field
          label="Full Name"
          name="name"
          value={form.name}
          onChange={handleChange}
          placeholder="Jane Smith"
        />
        <Field
          label="Location / City"
          name="location"
          value={form.location}
          onChange={handleChange}
          placeholder="Vilnius, Lithuania"
        />

        <button
          type="submit"
          className="w-full bg-extended-black text-white py-2.5 rounded-xl font-medium
                     hover:opacity-90 transition-opacity"
        >
          Save Changes
        </button>

        {saved && (
          <p className="text-center text-green-500 text-sm">Changes saved ✓</p>
        )}

        <div className="relative my-2">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200" />
          </div>
          <div className="relative flex justify-center">
            <span className="bg-white px-3 text-xs text-gray-400">Security</span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => alert('Password reset email sent (mock)')}
          className="w-full border-2 border-extended-black text-extended-black py-2.5 rounded-xl
                     font-medium hover:bg-extended-black hover:text-white transition-colors"
        >
          Reset Password
        </button>
      </form>
    </div>
  );
}

export default ProfilePage;
