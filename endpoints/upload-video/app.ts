import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { PutObjectCommand, S3Client } from '@aws-sdk/client-s3';

const client = new S3Client({});
export const lambdaHandler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    console.log(`Starting at: ${new Date()}`);
    try {
        const contentType = event.headers?.['Content-Type'] ?? 'vido/mp4';
        const videoBase64 = event.body;
        console.log({ path: event.path, contentType, videoBase64_IsTruthy: videoBase64 != null });
        if (!videoBase64 || typeof videoBase64 !== 'string') {
            return {
                statusCode: 400,
                body: JSON.stringify({
                    message: 'The request body is not valid base64 encoded `Content-Type: video/mp4`.',
                }),
            };
        }
        const fileName =
            event.queryStringParameters?.['fileName'] ??
            event.queryStringParameters?.['filename'] ??
            `vid_uploaded_${new Date().getTime()}.mp4`;
        const command = new PutObjectCommand({
            Bucket: 'radar-speed-sign',
            Key: fileName,
            Body: Buffer.from(videoBase64, 'base64'),
            ContentType: contentType,
            Metadata: { contentType },
        });
        await client.send(command);
        return {
            statusCode: 200,
            body: JSON.stringify({
                message: `Successfully uploaded ${fileName}`,
            }),
        };
    } catch (err) {
        console.log('an error occurred:', err);
        return {
            statusCode: 500,
            body: JSON.stringify({
                message: `InternalError: ${err}`,
            }),
        };
    }
};
