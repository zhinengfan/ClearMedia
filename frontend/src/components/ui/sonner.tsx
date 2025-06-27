import { Toaster as Sonner } from 'sonner';

type ToasterProps = React.ComponentProps<typeof Sonner>;

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="light"
      className="toaster group"
      position="top-right"
      expand={true}
      richColors={true}
      toastOptions={{
        duration: 4000,
        classNames: {
          toast:
            'group toast duration-700 group-[.toaster]:bg-white group-[.toaster]:text-gray-950 group-[.toaster]:border-gray-200 group-[.toaster]:shadow-lg data-[type=success]:bg-green-50 data-[type=success]:border-green-200 data-[type=success]:text-green-800 data-[type=error]:bg-red-50 data-[type=error]:border-red-200 data-[type=error]:text-red-800 data-[type=warning]:bg-yellow-50 data-[type=warning]:border-yellow-200 data-[type=warning]:text-yellow-800 data-[type=info]:bg-blue-50 data-[type=info]:border-blue-200 data-[type=info]:text-blue-800',
          description:
            'group-[.toast]:text-gray-600 data-[type=success]:text-green-700 data-[type=error]:text-red-700 data-[type=warning]:text-yellow-700 data-[type=info]:text-blue-700',
          actionButton:
            'group-[.toast]:bg-blue-600 group-[.toast]:text-white group-[.toast]:hover:bg-blue-700',
          cancelButton:
            'group-[.toast]:bg-gray-100 group-[.toast]:text-gray-600 group-[.toast]:hover:bg-gray-200',
          icon: 'data-[type=success]:text-green-600 data-[type=error]:text-red-600 data-[type=warning]:text-yellow-600 data-[type=info]:text-blue-600',
          closeButton:
            'data-[type=success]:border-green-200 data-[type=success]:text-green-600 data-[type=error]:border-red-200 data-[type=error]:text-red-600 data-[type=warning]:border-yellow-200 data-[type=warning]:text-yellow-600 data-[type=info]:border-blue-200 data-[type=info]:text-blue-600',
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
