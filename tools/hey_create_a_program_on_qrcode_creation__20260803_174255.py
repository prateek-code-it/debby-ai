import os
import qrcode

def generate_qr_from_file(file_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(file_path, 'r') as file:
        for line_number, line in enumerate(file, start=1):
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(line.strip())
            qr.make(fit=True)

            img = qr.make_image(fill='black', back_color='white')
            output_path = os.path.join(output_dir, f'line_{line_number}.png')
            img.save(output_path)
            print(f'Saved {output_path}')

if __name__ == "__main__":
    script_path = 'your_script.py'
    tools_directory = 'tools'
    generate_qr_from_file(script_path, tools_directory)